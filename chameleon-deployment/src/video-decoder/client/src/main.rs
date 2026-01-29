use proto::videodecode::video_decoder_client::VideoDecoderClient;
use proto::videodecode::{
    DecodeRequest, DecodeStart, VideoChunk, decode_request::Msg, decode_response,
};
use tokio::fs::File;
use tokio::io::AsyncReadExt;
use tokio::sync::mpsc;
use tokio_stream::wrappers::ReceiverStream;

use std::collections::HashMap;
use std::env;
use std::io::Write;
use std::path::Path;

const CHUNK_SIZE: usize = 1024 * 1024;

struct FrameBuffer {
    width: u32,
    height: u32,
    data: Vec<u8>,
    chunks_received: u32,
}

async fn send_video(
    video_path: &str,
    request_id: &str,
    tx: mpsc::Sender<DecodeRequest>,
) -> Result<(), anyhow::Error> {
    let filename = Path::new(video_path)
        .file_name()
        .and_then(|n| n.to_str())
        .unwrap_or("unknown")
        .to_string();

    tx.send(DecodeRequest {
        msg: Some(Msg::Start(DecodeStart {
            request_id: request_id.to_string(),
            filename,
        })),
    })
    .await?;

    let mut file = File::open(video_path).await?;
    let mut buffer = vec![0u8; CHUNK_SIZE];
    let mut offset: u64 = 0;

    loop {
        let bytes_read = file.read(&mut buffer).await?;

        if bytes_read == 0 {
            break;
        }

        let is_last = bytes_read < CHUNK_SIZE;

        let req = DecodeRequest {
            msg: Some(Msg::Chunk(VideoChunk {
                request_id: request_id.to_string(),
                offset,
                data: buffer[..bytes_read].to_vec(),
                eof: is_last,
            })),
        };

        tx.send(req).await?;

        offset += bytes_read as u64;

        if is_last {
            break;
        }
    }

    if offset > 0 {
        let last_chunk_was_full = offset as usize % CHUNK_SIZE == 0;

        if last_chunk_was_full {
            tx.send(DecodeRequest {
                msg: Some(Msg::Chunk(VideoChunk {
                    request_id: request_id.to_string(),
                    offset,
                    data: vec![],
                    eof: true,
                })),
            })
            .await?;
        }
    }

    Ok(())
}

fn write_ppm(
    output_dir: &str,
    frame_index: u64,
    width: u32,
    height: u32,
    data: &[u8],
) -> Result<(), anyhow::Error> {
    let path = format!("{}/frame{}.ppm", output_dir, frame_index);
    let mut file = std::fs::File::create(&path)?;

    write!(file, "P6\n{} {}\n255\n", width, height)?;
    file.write_all(data)?;

    println!("Wrote {}", path);
    Ok(())
}

#[tokio::main]
async fn main() -> Result<(), anyhow::Error> {
    let args: Vec<String> = env::args().collect();

    if args.len() < 3 {
        eprintln!("Usage: {} <video_path> <output_dir>", args[0]);
        std::process::exit(1);
    }

    let video_path = &args[1];
    let output_dir = &args[2];

    std::fs::create_dir_all(output_dir)?;

    let server_addr = env::var("SERVER_ADDR").unwrap_or_else(|_| "http://[::1]:50051".to_string());
    let mut client = VideoDecoderClient::connect(server_addr).await?;

    let request_id = uuid::Uuid::new_v4().to_string();
    let (tx, rx) = mpsc::channel(32);

    let video_path_clone = video_path.clone();
    let request_id_clone = request_id.clone();

    tokio::spawn(async move {
        if let Err(e) = send_video(&video_path_clone, &request_id_clone, tx).await {
            eprintln!("Error sending video: {}", e);
        }
    });

    let request = tonic::Request::new(ReceiverStream::new(rx));
    let mut response_stream = client.decode(request).await?.into_inner();

    let mut frame_buffers: HashMap<u64, FrameBuffer> = HashMap::new();

    while let Some(response) = response_stream.message().await? {
        match response.msg {
            Some(decode_response::Msg::FrameChunk(chunk)) => {
                let info = chunk.info.as_ref().unwrap();
                let frame_idx = info.frame_index;

                let entry = frame_buffers
                    .entry(frame_idx)
                    .or_insert_with(|| FrameBuffer {
                        width: info.width,
                        height: info.height,
                        data: Vec::new(),
                        chunks_received: 0,
                    });

                entry.data.extend_from_slice(&chunk.data);
                entry.chunks_received += 1;

                if entry.chunks_received == chunk.chunk_count {
                    let frame = frame_buffers.remove(&frame_idx).unwrap();

                    write_ppm(
                        output_dir,
                        frame_idx,
                        frame.width,
                        frame.height,
                        &frame.data,
                    )?;
                }
            }

            Some(decode_response::Msg::Progress(progress)) => {
                println!(
                    "Progress: {} bytes received, {} frames decoded",
                    progress.bytes_received, progress.frames_decoded
                );
            }

            Some(decode_response::Msg::Error(error)) => {
                eprintln!("Decode error: {} (code: {})", error.message, error.code);
                return Err(anyhow::anyhow!("Decode failed: {}", error.message));
            }

            Some(decode_response::Msg::Done(done)) => {
                println!("Decode complete: {} frames decoded", done.frames_decoded);
            }

            None => {}
        }
    }

    Ok(())
}

use proto::videodecode::video_decoder_server::{VideoDecoder, VideoDecoderServer};
use proto::videodecode::{
    DecodeDone, DecodeError, DecodeErrorCode, DecodeRequest, DecodeResponse, FrameChunk, FrameInfo,
    PixelFormat, Progress, decode_request::Msg,
};
use tokio::sync::mpsc;
use tokio_stream::wrappers::ReceiverStream;
use tonic::{Request, Response, Status, Streaming, transport::Server};

use ffmpeg::format;
use ffmpeg::media::Type;
use ffmpeg::software::scaling::{context::Context as ScalerContext, flag::Flags};
use ffmpeg::util::format::Pixel;
use ffmpeg::util::frame::video::Video;
use ffmpeg_next as ffmpeg;

use std::io::Write;
use tempfile::NamedTempFile;

const FRAME_CHUNK_SIZE: usize = 1024 * 1024;

#[derive(Default)]
pub struct MyVideoDecoder;

impl MyVideoDecoder {
    fn decode_video(
        &self,
        request_id: String,
        video_path: &str,
        tx: mpsc::Sender<Result<DecodeResponse, Status>>,
    ) -> Result<u64, String> {
        ffmpeg::init().map_err(|e| format!("Failed to init ffmpeg: {}", e))?;

        let mut ictx =
            format::input(video_path).map_err(|e| format!("Failed to open video: {}", e))?;

        let input = ictx
            .streams()
            .best(Type::Video)
            .ok_or("No video stream found")?;

        let video_stream_index = input.index();

        let context_decoder = ffmpeg::codec::context::Context::from_parameters(input.parameters())
            .map_err(|e| format!("Failed to create decoder context: {}", e))?;

        let mut video_decoder = context_decoder
            .decoder()
            .video()
            .map_err(|e| format!("Failed to create video decoder: {}", e))?;

        let mut scaler = ScalerContext::get(
            video_decoder.format(),
            video_decoder.width(),
            video_decoder.height(),
            Pixel::RGB24,
            video_decoder.width(),
            video_decoder.height(),
            Flags::BILINEAR,
        )
        .map_err(|e| format!("Failed to create scaler: {}", e))?;

        let mut frame_index: u64 = 0;
        let tx_clone = tx.clone();
        let request_id_clone = request_id.clone();

        let mut process_frames = |decoder: &mut ffmpeg::decoder::Video| -> Result<(), String> {
            loop {
                let mut frame = Video::empty();

                match decoder.receive_frame(&mut frame) {
                    Ok(_) => {
                        let mut converted = Video::empty();

                        scaler
                            .run(&frame, &mut converted)
                            .map_err(|e| format!("Scaler error: {}", e))?;

                        let width = converted.width();
                        let height = converted.height();
                        let stride = converted.stride(0);
                        let data = converted.data(0);

                        let frame_info = FrameInfo {
                            frame_index,
                            width,
                            height,
                            pixel_format: PixelFormat::Rgb24.into(),
                            stride: stride as u32,
                            pts: frame.pts().unwrap_or(0),
                        };

                        let total_bytes = data.len();
                        let chunk_count =
                            ((total_bytes + FRAME_CHUNK_SIZE - 1) / FRAME_CHUNK_SIZE) as u32;

                        for (chunk_idx, chunk_data) in data.chunks(FRAME_CHUNK_SIZE).enumerate() {
                            let frame_chunk = FrameChunk {
                                request_id: request_id_clone.clone(),
                                info: Some(frame_info.clone()),
                                chunk_index: chunk_idx as u32,
                                chunk_count,
                                data: chunk_data.to_vec(),
                            };

                            let response = DecodeResponse {
                                msg: Some(proto::videodecode::decode_response::Msg::FrameChunk(
                                    frame_chunk,
                                )),
                            };

                            if tx_clone.blocking_send(Ok(response)).is_err() {
                                return Err("Client disconnected".to_string());
                            }
                        }

                        frame_index += 1;
                    }

                    Err(ffmpeg::Error::Other { errno: 11 }) => break, // EAGAIN
                    Err(ffmpeg::Error::Eof) => break,
                    Err(e) => return Err(format!("Decode error: {}", e)),
                }
            }
            Ok(())
        };

        for (stream, packet) in ictx.packets() {
            if stream.index() == video_stream_index {
                video_decoder
                    .send_packet(&packet)
                    .map_err(|e| format!("Failed to send packet: {}", e))?;
                process_frames(&mut video_decoder)?;
            }
        }

        video_decoder
            .send_eof()
            .map_err(|e| format!("Failed to send EOF: {}", e))?;
        process_frames(&mut video_decoder)?;

        Ok(frame_index)
    }
}

#[tonic::async_trait]
impl VideoDecoder for MyVideoDecoder {
    type DecodeStream = ReceiverStream<Result<DecodeResponse, Status>>;

    async fn decode(
        &self,
        request: Request<Streaming<DecodeRequest>>,
    ) -> Result<Response<Self::DecodeStream>, Status> {
        let mut stream = request.into_inner();
        let (tx, rx) = mpsc::channel(32);

        tokio::spawn(async move {
            let mut request_id = String::new();
            let mut temp_file: Option<NamedTempFile> = None;
            let mut bytes_received: u64 = 0;

            while let Ok(Some(req)) = stream.message().await {
                match req.msg {
                    Some(Msg::Start(start)) => {
                        request_id = start.request_id.clone();

                        temp_file = match NamedTempFile::new() {
                            Ok(f) => Some(f),

                            Err(e) => {
                                let _ = tx
                                    .send(Ok(DecodeResponse {
                                        msg: Some(proto::videodecode::decode_response::Msg::Error(
                                            DecodeError {
                                                request_id: request_id.clone(),
                                                code: DecodeErrorCode::Internal.into(),
                                                message: format!(
                                                    "Failed to create temp file: {}",
                                                    e
                                                ),
                                            },
                                        )),
                                    }))
                                    .await;
                                return;
                            }
                        };

                        println!(
                            "Started decode request: {} (filename: {})",
                            request_id, start.filename
                        );
                    }

                    Some(Msg::Chunk(chunk)) => {
                        if let Some(ref mut file) = temp_file {
                            if let Err(e) = file.write_all(&chunk.data) {
                                let _ = tx
                                    .send(Ok(DecodeResponse {
                                        msg: Some(proto::videodecode::decode_response::Msg::Error(
                                            DecodeError {
                                                request_id: request_id.clone(),
                                                code: DecodeErrorCode::Internal.into(),
                                                message: format!("Failed to write chunk: {}", e),
                                            },
                                        )),
                                    }))
                                    .await;
                                return;
                            }

                            bytes_received += chunk.data.len() as u64;

                            let _ = tx
                                .send(Ok(DecodeResponse {
                                    msg: Some(proto::videodecode::decode_response::Msg::Progress(
                                        Progress {
                                            request_id: request_id.clone(),
                                            bytes_received,
                                            frames_decoded: 0,
                                        },
                                    )),
                                }))
                                .await;

                            if chunk.eof {
                                if let Err(e) = file.flush() {
                                    let _ = tx
                                        .send(Ok(DecodeResponse {
                                            msg: Some(
                                                proto::videodecode::decode_response::Msg::Error(
                                                    DecodeError {
                                                        request_id: request_id.clone(),
                                                        code: DecodeErrorCode::Internal.into(),
                                                        message: format!(
                                                            "Failed to flush temp file: {}",
                                                            e
                                                        ),
                                                    },
                                                ),
                                            ),
                                        }))
                                        .await;
                                    return;
                                }

                                let video_path = file.path().to_string_lossy().to_string();
                                let tx_decode = tx.clone();
                                let req_id = request_id.clone();

                                let decoder = MyVideoDecoder;

                                let decode_result = tokio::task::spawn_blocking(move || {
                                    decoder.decode_video(req_id.clone(), &video_path, tx_decode)
                                })
                                .await;

                                match decode_result {
                                    Ok(Ok(frames_decoded)) => {
                                        let _ = tx
                                            .send(Ok(DecodeResponse {
                                                msg: Some(
                                                    proto::videodecode::decode_response::Msg::Done(
                                                        DecodeDone {
                                                            request_id: request_id.clone(),
                                                            frames_decoded,
                                                        },
                                                    ),
                                                ),
                                            }))
                                            .await;
                                    }

                                    Ok(Err(e)) => {
                                        let _ = tx
                                            .send(Ok(DecodeResponse {
                                                msg: Some(
                                                    proto::videodecode::decode_response::Msg::Error(
                                                        DecodeError {
                                                            request_id: request_id.clone(),
                                                            code: DecodeErrorCode::DecodeError
                                                                .into(),
                                                            message: e,
                                                        },
                                                    ),
                                                ),
                                            }))
                                            .await;
                                    }

                                    Err(e) => {
                                        let _ = tx
                                            .send(Ok(DecodeResponse {
                                                msg: Some(
                                                    proto::videodecode::decode_response::Msg::Error(
                                                        DecodeError {
                                                            request_id: request_id.clone(),
                                                            code: DecodeErrorCode::Internal.into(),
                                                            message: format!(
                                                                "Task panicked: {}",
                                                                e
                                                            ),
                                                        },
                                                    ),
                                                ),
                                            }))
                                            .await;
                                    }
                                }
                                return;
                            }
                        }
                    }

                    None => {}
                }
            }
        });

        Ok(Response::new(ReceiverStream::new(rx)))
    }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let addr = "[::]:50051".parse()?;

    println!("Video decoder server listening on {}", addr);

    Server::builder()
        .add_service(VideoDecoderServer::new(MyVideoDecoder::default()))
        .serve(addr)
        .await?;

    Ok(())
}

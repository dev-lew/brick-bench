extern crate ffmpeg_next as ffmpeg;

use crate::ffmpeg::util::format::Pixel;
use anyhow::{Result, anyhow};
use ffmpeg::Error;
use ffmpeg::codec::context;
use ffmpeg::codec::decoder;
use ffmpeg::format;
use ffmpeg::media::Type;
use ffmpeg::software::scaling::{context::Context, flag::Flags};
use ffmpeg::util::frame::video::Video;

use std::env;
use std::fs::File;
use std::io::prelude::*;
use std::iter;

fn get_stream<'a>(
    av_input_format: &'a format::context::Input,
    stream_type: Type,
) -> Result<ffmpeg::Stream<'a>> {
    av_input_format
        .streams()
        .best(stream_type)
        .ok_or_else(|| anyhow!("No {:?} stream found", stream_type))
}

fn convert_pixel_format(video: &decoder::Video, to: Pixel) -> Result<Context> {
    Ok(Context::get(
        video.format(),
        video.width(),
        video.height(),
        to,
        video.width(),
        video.height(),
        Flags::BILINEAR,
    )?)
}

fn decoded_frames(decoder: &mut ffmpeg::decoder::Video) -> impl Iterator<Item = Video> {
    iter::from_fn(|| {
        let mut decoded = Video::empty();

        match decoder.receive_frame(&mut decoded) {
            Ok(_) => Some(decoded),
            Err(Error::Eof) => None,

            // We hope we don't get AVERROR(EAGAIN)
            _ => panic!(),
        }
    })
}

fn convert_frame(scaler: &mut Context, frame: Video) -> Video {
    let mut converted = Video::empty();

    scaler.run(&frame, &mut converted).unwrap();
    converted
}

fn write_ppm(frame: &Video, index: usize) -> Result<()> {
    let mut file = File::create(format!("frame{}.ppm", index))?;

    file.write_all(format!("P6\n{} {}\n255\n", frame.width(), frame.height()).as_bytes())?;
    file.write_all(frame.data(0))?;

    Ok(())
}

fn main() -> Result<()> {
    ffmpeg::init().unwrap();

    let video_path = env::args().nth(1).unwrap();

    let mut ictx = format::input(&video_path)?;
    let input = get_stream(&ictx, Type::Video)?;
    let video_stream_index = input.index();

    let context_decoder = context::Context::from_parameters(input.parameters()).unwrap();
    let mut video_decoder = context_decoder.decoder().video()?;

    // Convert decoded frames to RGB24 for PPM output
    let mut scaler: Context = convert_pixel_format(&video_decoder, Pixel::RGB24).unwrap();

    for (stream, packet) in ictx.packets() {
        if stream.index() == video_stream_index {
            video_decoder.send_packet(&packet)?;

            let processed_frames =
                decoded_frames(&mut video_decoder).map(|frame| convert_frame(&mut scaler, frame));

            for (idx, frame) in processed_frames.enumerate() {
                write_ppm(&frame, idx).unwrap();
            }
        }
    }

    Ok(())
}

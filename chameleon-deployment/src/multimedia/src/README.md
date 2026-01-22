# Multimedia

## General steps for video decoding with libavcodec
The following list notes the original C API as well

1. Initialize FFmpeg
    * `av_register_all()`
    * Rust: `ffmpeg::init()`

2. Open input container (demuxing)
    * `avformat_open_input`
    * `avformat_find_stream_info`
    * Rust: `format::input(path)`

3. Select a stream
   * Iterate `AVFormatContext->streams`
   * Pick a stream whose `codecpar->codec_type == AVMEDIA_TYPE_VIDEO`
   * Rust: `streams().best(Type::Video)`

4. Create decoder context
   * Allocate `AVCodecContext`
   * Copy parameters from `AVStream->codecpar`
   * Find decoder via codec ID
   * Open decoder with `avcodec_open2`
   * Rust: `Context::from_parameters(...).decoder().video()`

5. Read packets
   * `av_read_frame`
   * Rust iterator: `ictx.packets()`

6. Send packets to decoder
   * `avcodec_send_packet`

7. Receive decoded frames
   * `avcodec_receive_frame`
   * Loop until EAGAIN or EOF

8. Flush decoder
   * `avcodec_send_packet(ctx, NULL)`
   * Drain remaining frames

### Wrapper types
Type-by-type breakdown (Rust ffmpeg-next ↔ FFmpeg C API)

1. `format::context::Input`

   C equivalent: `AVFormatContext`

   Role:
   * Represents the opened media container (MP4, MKV, AVI, etc.)
   * Owns demuxers and protocol state
   * Produces compressed packets

   Contains / manages:
   * streams[]            → array of AVStream*
   * metadata             → container-level metadata
   * IO context           → file, network, or custom reader

   Key operations:
   * packets()            → wraps `av_read_frame()`
   * streams()            → exposes AVStream list

2. `ffmpeg::Stream`

   C equivalent: `AVStream`

   Role:
   * Represents a single elementary stream inside the container
     (video, audio, subtitle, data)

   Contains:
   * index                → stream index used in `AVPacket`
   * time_base            → units for timestamps
   * codecpar             → `AVCodecParameters`

   Key usage:
   * Used to select decoder type
   * Provides codec parameters for decoder initialization

3. `codec::context::Context`

   C equivalent: `AVCodecContext`

   Role:
   * Holds codec configuration and runtime state
   * Central object for encoding or decoding

   Contains:
   * codec_id             → identifies codec (H264, HEVC, VP9, etc.)
   * width / height       → video dimensions
   * pix_fmt              → pixel format of decoded frames
   * extradata            → codec headers (SPS/PPS, etc.)
   * internal buffers     → reference frames, reorder queues

   Lifecycle:
   * Allocated
   * Filled from `AVCodecParameters`
   * Opened with `avcodec_open2`
   * Fed packets / produces frames

4. `decoder::Video`

   C equivalent: `AVCodecContext` (video-specialized view)

   Role:
   * Typed wrapper enforcing `AVMEDIA_TYPE_VIDEO`
   * Provides video-specific decode API

   Key operations:
   * `send_packet()`        → `avcodec_send_packet()`
   * `receive_frame()`      → `avcodec_receive_frame()`

   Notes:
   * One packet may produce 0..N frames
   * Frames may be delayed due to B-frames

5. `format::Packet`

   C equivalent: `AVPacket`

   Role:
   * Holds compressed bitstream data read from the container

   Contains:
   * data / size          → encoded bytes
   * stream_index         → identifies target stream
   * pts / dts            → timestamps
   * flags                → keyframe, corruption, etc.

   Notes:
   * Packet boundaries do NOT equal frame boundaries
   * Must be sent in demuxer order

6. `util::frame::video::Video`

   C equivalent: `AVFrame`

   Role:
   * Holds a decoded, uncompressed video frame

   Contains:
   * data[0..7]           → pointers to image planes
   * linesize[0..7]       → stride per plane
   * width / height       → frame size
   * format               → `AVPixelFormat`
   * pts                  → presentation timestamp

   Common layouts:
   * YUV420P: 3 planes (Y, U, V)
   * NV12:   2 planes (Y, UV)
   * RGB24:  1 packed plane

   Notes:
   * Frame memory may be reference-counted
   * Reused internally by the decoder

7. `util::format::Pixel`

   C equivalent: `enum AVPixelFormat`

   Role:
   * Identifies pixel layout and color encoding

   Examples:
   * `AV_PIX_FMT_YUV420P`
   * `AV_PIX_FMT_NV12`
   * `AV_PIX_FMT_RGB24`

   Notes:
   * Decoders output codec-native formats
   * Display or file output often requires conversion

8. `software::scaling::Context`

   C equivalent: `struct SwsContext` (libswscale)

   Role:
   * Converts pixel formats
   * Scales images
   * Handles colorspace conversion

   Created via:
   * `sws_getContext()`

   Used via:
   * `sws_scale()`

   Notes:
   - Stateless per-call, but expensive to create
   - Should be reused for all frames with same geometry

9. `media::Type`

   C equivalent: `enum AVMediaType`

   Role:
   * Identifies stream category

   Values:
   * `AVMEDIA_TYPE_VIDEO`
   * `AVMEDIA_TYPE_AUDIO`
   * `AVMEDIA_TYPE_SUBTITLE`

   Used for:
   * Stream selection
   * Decoder specialization

10. Error handling (implicit)

    C equivalents:
    * `AVERROR(EAGAIN)`
    * `AVERROR_EOF`

    Meaning:
    * EAGAIN: decoder needs more input packets
    * EOF: decoder fully flushed

    Notes:
    - Normal control flow, not fatal errors

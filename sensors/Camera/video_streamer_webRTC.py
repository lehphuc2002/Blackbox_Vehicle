import asyncio
import json
import logging
from aiohttp import web
from av import VideoFrame
from aiortc import MediaStreamTrack, RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from fractions import Fraction
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
from pathlib import Path
import numpy as np

# Initialize GStreamer
Gst.init(None)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GStreamerVideoStreamTrack(VideoStreamTrack):
    def __init__(self):
        super().__init__()
        self._pipeline = None
        self._sample = None
        self._sample_lock = asyncio.Lock()
        self._main_loop = None
        self._init_pipeline()

    def _init_pipeline(self):
        pipeline_str = (
            'v4l2src device=/dev/video0 ! '
            'video/x-raw,width=640,height=480,framerate=30/1 ! '
            'videoconvert ! '
            'video/x-raw,format=RGB ! '
            'appsink name=sink emit-signals=True max-buffers=1 drop=True'
        )
        
        self._pipeline = Gst.parse_launch(pipeline_str)
        self.sink = self._pipeline.get_by_name('sink')
        self.sink.connect('new-sample', self._on_new_sample)
        
        # Start pipeline
        self._pipeline.set_state(Gst.State.PLAYING)

    def _on_new_sample(self, sink):
        sample = sink.emit('pull-sample')
        if sample:
            asyncio.run_coroutine_threadsafe(self._set_sample(sample), self._loop)
        return Gst.FlowReturn.OK

    async def _set_sample(self, sample):
        async with self._sample_lock:
            self._sample = sample

    async def recv(self):
        pts, time_base = await self.next_timestamp()

        async with self._sample_lock:
            if self._sample:
                buf = self._sample.get_buffer()
                caps = self._sample.get_caps()
                
                # Get buffer data
                success, map_info = buf.map(Gst.MapFlags.READ)
                if not success:
                    return None
                
                try:
                    # Get width and height from caps
                    structure = caps.get_structure(0)
                    width = structure.get_value('width')
                    height = structure.get_value('height')
                    
                    # Create numpy array from buffer data
                    data = np.ndarray(
                        (height, width, 3),
                        buffer=map_info.data,
                        dtype=np.uint8
                    )
                    
                    # Create VideoFrame
                    frame = VideoFrame.from_ndarray(data, format='rgb24')
                    frame.pts = pts
                    frame.time_base = time_base
                    
                    return frame
                finally:
                    buf.unmap(map_info)

    def __del__(self):
        if self._pipeline:
            self._pipeline.set_state(Gst.State.NULL)

class WebRTCServer:
    def __init__(self):
        self.pcs = set()
        self._video_tracks = set()

    async def index(self, request):
        template_path = Path(__file__).parent / "templates" / "index_camera_webRTC.html"
        with open(template_path) as f:
            content = f.read()
        return web.Response(content_type="text/html", text=content)

    async def offer(self, request):
        params = await request.json()
        offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

        pc = RTCPeerConnection()
        self.pcs.add(pc)

        @pc.on("connectionstatechange")
        async def on_connectionstatechange():
            logger.info(f"Connection state is {pc.connectionState}")
            if pc.connectionState == "failed":
                await pc.close()
                self.pcs.discard(pc)

        # Create video track
        video = GStreamerVideoStreamTrack()
        self._video_tracks.add(video)
        pc.addTrack(video)

        await pc.setRemoteDescription(offer)
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)

        return web.Response(
            content_type="application/json",
            text=json.dumps({
                "sdp": pc.localDescription.sdp,
                "type": pc.localDescription.type
            })
        )

    async def candidate(self, request):
        return web.Response(text="OK")

    async def on_shutdown(self, app):
        # Close peer connections
        coros = [pc.close() for pc in self.pcs]
        await asyncio.gather(*coros)
        self.pcs.clear()

        # Clean up video tracks
        for track in self._video_tracks:
            track.__del__()
        self._video_tracks.clear()

def init_app():
    server = WebRTCServer()
    app = web.Application()
    app.router.add_get("/", server.index)
    app.router.add_post("/offer", server.offer)
    app.router.add_post("/candidate", server.candidate)
    app.on_shutdown.append(server.on_shutdown)
    return app

if __name__ == "__main__":
    try:
        # Create event loop
        loop = asyncio.get_event_loop()
        app = init_app()
        web.run_app(app, host="0.0.0.0", port=5000, access_log=None)
    except Exception as e:
        logger.error(f"Server error: {str(e)}")
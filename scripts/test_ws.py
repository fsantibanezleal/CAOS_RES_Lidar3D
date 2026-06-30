import asyncio, json, websockets
async def main():
    uri="ws://127.0.0.1:8120/ws/stream"
    async with websockets.connect(uri, max_size=None) as ws:
        await ws.send(json.dumps({"source_id":"oxford","params":{"max_frames":16,"decimation":8}}))
        count=0
        async for msg in ws:
            m=json.loads(msg)
            t=m["type"]
            if t=="start": print("START", m.get("n_frames"),"frames, engine",m.get("engine"))
            elif t=="frame":
                count+=1
                if count<=2 or m["idx"]%4==0:
                    print(f"  frame {m['idx']:2d} pts={m['n_points']:4d} fps={m['fps']:.1f} vram={m['vram_gb']:.1f} pose_t=({m['pose_c2w'][3]:+.2f},{m['pose_c2w'][7]:+.2f},{m['pose_c2w'][11]:+.2f}) depth={'ok' if m['depth_png'].startswith('data:image') else 'NO'}")
            elif t=="done": print("DONE frames=",count); break
            elif t=="error": print("ERROR", m.get("message")); break
asyncio.run(main())
print("WS_TEST_OK")

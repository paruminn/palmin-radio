#!/usr/bin/env python3
"""Generate one MP3 from a Palmin Radio episode using COEIROINK's local API."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen


API = "http://127.0.0.1:50032"
CASTERS = {
    "leticia": ("アンジーさん", "のーまる"),
    "fille": ("AI声優-朱花", "のーまるv2"),
    "shero": ("アルマちゃん", "表-v2"),
}


def get_styles() -> dict[tuple[str, str], tuple[str, int]]:
    with urlopen(f"{API}/v1/speakers", timeout=10) as response:
        speakers = json.load(response)
    found: dict[tuple[str, str], tuple[str, int]] = {}
    for speaker in speakers:
        for style in speaker.get("styles", []):
            found[(speaker["speakerName"], style["styleName"])] = (
                speaker["speakerUuid"], int(style["styleId"])
            )
    return found


def ordered_lines(episode: dict) -> list[tuple[str, int | None, int, dict | None]]:
    groups = [("opening", None, episode.get("opening", []))]
    groups.extend(("news", i, item.get("lines", [])) for i, item in enumerate(episode.get("news", [])))
    groups.append(("closing", None, episode.get("closing", [])))
    ordered = []
    segment_index = 0
    for kind, index, lines in groups:
        if not lines:
            continue
        ordered.append((kind, index, segment_index, None))
        for line in lines:
            if not isinstance(line, dict) or not line.get("say"):
                raise ValueError("すべての読み上げ文に say と speaker を設定してください。")
            if line.get("speaker") not in CASTERS:
                raise ValueError(f"speaker は {', '.join(CASTERS)} のいずれかにしてください。")
            ordered.append(("line", index, segment_index, line))
        segment_index += 1
    return ordered


def measure(ffprobe: str, wav: Path) -> float:
    result = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(wav)],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())


def synthesize(text: str, speaker_uuid: str, style_id: int, destination: Path) -> None:
    body = json.dumps(
        {
            "volumeScale": 1,
            "pitchScale": 0,
            "intonationScale": 1,
            "prePhonemeLength": 0.1,
            "postPhonemeLength": 0.2,
            "outputSamplingRate": 44100,
            "sampledIntervalValue": 0,
            "adjustedF0": [],
            "processingAlgorithm": "coeiroink",
            "speakerUuid": speaker_uuid,
            "styleId": style_id,
            "text": text,
            "prosodyDetail": [],
            "speedScale": 1,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    request = Request(
        f"{API}/v1/synthesis",
        data=body,
        headers={"Accept": "audio/wav", "Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=120) as response:
        destination.write_bytes(response.read())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("episode", type=Path, help="episodes/YYYY-MM-DD-ja.json")
    parser.add_argument("--ffmpeg", default="ffmpeg", help="FFmpeg executable path")
    parser.add_argument("--ffprobe", default="ffprobe", help="FFprobe executable path")
    parser.add_argument("--output", type=Path, help="MP3 output path (default: audio/<episode-name>.mp3)")
    args = parser.parse_args()

    episode_path = args.episode.resolve()
    episode = json.loads(episode_path.read_text(encoding="utf-8-sig"))
    ordered = ordered_lines(episode)
    if not any(item[0] == "line" for item in ordered):
        raise ValueError("読み上げる文がありません。")

    styles = get_styles()
    output = args.output or (episode_path.parent.parent / "audio" / f"{episode_path.stem}.mp3")
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    timed_lines = []
    segments = []
    current = 0.0
    with tempfile.TemporaryDirectory(prefix="palmin-radio-") as temp_name:
        temp = Path(temp_name)
        concat_file = temp / "files.txt"
        wavs = []
        for item in ordered:
            kind, index, segment_index, line = item
            if kind != "line":
                segments.append({"kind": kind, "index": index, "start": round(current, 3), "end": round(current, 3)})
                continue
            name, style = CASTERS[line["speaker"]]
            if (name, style) not in styles:
                raise RuntimeError(f"COEIROINKに {name} の {style} スタイルがありません。")
            speaker_uuid, style_id = styles[(name, style)]
            wav = temp / f"{len(wavs):04d}.wav"
            synthesize(line["say"], speaker_uuid, style_id, wav)
            duration = measure(args.ffprobe, wav)
            end = current + duration
            timed_lines.append(
                {"start": round(current, 3), "end": round(end, 3), "show": line.get("show", line["say"]), "part": segment_index}
            )
            segment = segments[segment_index]
            segment["end"] = round(end, 3)
            current = end
            wavs.append(wav)

        concat_file.write_text(
            "".join(f"file '{str(wav).replace(os.sep, '/')}'\n" for wav in wavs),
            encoding="utf-8",
        )
        staged_output = temp / "episode.mp3"
        subprocess.run(
            [args.ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-codec:a", "libmp3lame", "-b:a", "128k", str(staged_output)],
            check=True,
        )
        staged_output.replace(output)

    episode["seconds"] = round(current, 3)
    episode["lines_timed"] = timed_lines
    episode["segments"] = segments
    episode["made_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
    episode_path.write_text(json.dumps(episode, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest_path = episode_path.parent.parent / "episodes.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    entry = next((item for item in manifest if item.get("date") == episode.get("date")), None)
    if entry is not None:
        lang = episode.get("lang", "ja")
        target = entry.get(lang) if isinstance(entry.get(lang), dict) else entry
        target["title"] = episode.get("title", target.get("title", ""))
        target["seconds"] = episode["seconds"]
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"音声を作成しました: {output}")
    print(f"長さ: {episode['seconds']} 秒 / 台詞: {len(timed_lines)} 個")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        raise SystemExit(f"音声を作成できませんでした: {error}")

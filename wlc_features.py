"""Compute the APK features an on-device workload classifier looks at.

Reads only the APK's file list (nothing is extracted or modified) and prints
the size and count features, so you can see how close your APK is to being
classified as a game. Feed the output to wlc_score.py.

Usage:
    python wlc_features.py app.apk [--activities N]

--activities is the number of <activity> entries in the merged manifest
(a Flutter or single-activity app is usually 1 or 2). Default: 2.
"""
import argparse
import json
import zipfile

MB = 1048576.0
# Native libraries of common game engines. Their presence counts toward "game".
ENGINE_LIBRARIES = {
    "libopenal.so", "libfmod.so", "libgame.so", "game.so", "libunity.so",
    "libue4.so", "libmono.so", "libgodot_android.so", "libgdx.so",
    "liblove.so", "libcorona.so", "libcocos2dcpp.so", "libcocos2dlua.so",
    "libyoyo.so",
}


def features(path, activities):
    total = assets = res = lib = 0
    asset_count = res_count = lib_count = 0
    engines = set()
    for entry in zipfile.ZipFile(path).infolist():
        name, size = entry.filename.lower(), entry.file_size
        total += size
        if name.startswith("lib/"):
            lib_count += 1
            lib += size
            base = name.rsplit("/", 1)[-1]
            if base in ENGINE_LIBRARIES:
                engines.add(base)
        if name.startswith("assets/"):
            asset_count += 1
            assets += size
        if name.startswith("res/") or name.startswith("r/"):
            res_count += 1
            res += size
    return {
        "total_mb": round(total / MB, 2),
        "activities": activities,
        "asset_count": asset_count,
        "asset_mb": round(assets / MB, 2),
        "res_count": res_count,
        "res_mb": round(res / MB, 2),
        "lib_count": lib_count,
        "lib_mb": round(lib / MB, 2),
        "engine_libraries": sorted(engines),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("apk")
    parser.add_argument("--activities", type=int, default=2)
    args = parser.parse_args()
    print(json.dumps(features(args.apk, args.activities), indent=2))


if __name__ == "__main__":
    main()

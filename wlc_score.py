"""Score an APK with the workload classifier model pulled from your own phone.

The model is not included in this repository. Pull it from your device:

    adb pull /system_ext/etc/perf/wlc_model.tflite

Then:

    pip install ai-edge-litert numpy
    python wlc_score.py app.apk --model wlc_model.tflite

The score is the model's output (0..1). On the phones we tested, 0.5 and
above is treated as a game.
"""
import argparse

import numpy as np

from wlc_features import features

# Each raw feature is divided by a fixed value before it goes into the model.
# These values come from the classifier on HyperOS 3 (Snapdragon); other
# builds may use different ones.
SCALE = [4308.229, 1892.0, 57109.0, 4287.57, 0.99520475, 478.77765, 19764.0,
         88.05, 0.99349016, 473.99948, 872.0, 564.94495, 0.96120644, 3.0, 3.0,
         1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]


def vector(f, gles=0, is_game=False, large_heap=False):
    total, acts = f["total_mb"], f["activities"]
    assets, res, lib = f["asset_mb"], f["res_mb"], f["lib_mb"]
    return [
        total, acts, f["asset_count"], assets, assets / total,
        total / (acts + 1), f["res_count"], res, res / total,
        assets / (acts + 1), f["lib_count"], lib, lib / total,
        len(f["engine_libraries"]),
        0.0,  # multitouch, accelerometer or gamepad declared in the manifest
        0.0,  # camera declared
        0.0,  # NFC or step sensors declared
        0.0,  # Google Play Games metadata
        1.0 if gles == 2 else 0.0,
        1.0 if gles == 3 else 0.0,
        1.0 if is_game else 0.0,  # android:appCategory="game" or isGame
        1.0 if large_heap else 0.0,
    ]


def score(model, raw):
    from ai_edge_litert.interpreter import Interpreter
    interpreter = Interpreter(model_path=model)
    interpreter.allocate_tensors()
    x = np.array([[v / s for v, s in zip(raw, SCALE)]], dtype=np.float32)
    interpreter.set_tensor(interpreter.get_input_details()[0]["index"], x)
    interpreter.invoke()
    return float(interpreter.get_tensor(interpreter.get_output_details()[0]["index"])[0][0])


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("apk")
    parser.add_argument("--model", required=True, help="wlc_model.tflite pulled from your phone")
    parser.add_argument("--activities", type=int, default=2)
    parser.add_argument("--gles", type=int, choices=(0, 2, 3), default=0,
                        help="glEsVersion declared in the manifest, if any")
    parser.add_argument("--is-game", action="store_true")
    parser.add_argument("--large-heap", action="store_true")
    parser.add_argument("--sweep", action="store_true",
                        help="also show the score with smaller assets/")
    args = parser.parse_args()
    f = features(args.apk, args.activities)
    s = score(args.model, vector(f, args.gles, args.is_game, args.large_heap))
    print(f"assets/ {f['asset_mb']:.2f} MB, total {f['total_mb']:.2f} MB")
    print(f"score {s:.3f} -> {'GAME' if s >= 0.5 else 'not a game'}")
    if args.sweep:
        other = f["total_mb"] - f["asset_mb"]
        for target in (100, 50, 20, 15, 10, 8, 7, 5, 3, 1):
            if target >= f["asset_mb"]:
                continue
            g = dict(f, asset_mb=target, total_mb=other + target)
            t = score(args.model, vector(g, args.gles, args.is_game, args.large_heap))
            print(f"  if assets/ were {target:>3} MB: {t:.3f}")


if __name__ == "__main__":
    main()

"""Audite un dataset et le découpe en train / val / test SANS fuite de données.

Deux garde-fous essentiels avant l'entraînement :
  1. Anti-fuite : les quasi-doublons (même photo ré-encodée / redimensionnée /
     watermarkée) sont regroupés via un hash perceptuel (dHash) et placés
     ENTIÈREMENT dans le même split. Sinon la même image se retrouve en train
     ET en test, ce qui gonfle artificiellement le score.
  2. Stratification : chaque classe (type/marque/modèle) est répartie
     proportionnellement entre les trois splits.

Ne déplace ni ne copie rien : écrit un manifeste <dataset>/dataset_split.csv
avec les colonnes  file,type,brand,model,split.

Dépendances :  pip install imagehash pillow

Exemples :
    python split_dataset.py dataset_moto
    python split_dataset.py dataset_moto -val 0.15 -test 0.15 -seed 42
"""
import argparse
import csv
import os
import random
from collections import defaultdict

import imagehash
from PIL import Image

from utils.utils import FileUtil

REJECTED_DIRNAME = "_rejected"
MIN_PER_CLASS = 4   # en-dessous, la classe part entièrement en train (trop petite)


def read_samples(root):
    """(file, type, brand, model) pour chaque image, depuis labels.csv si présent,
    sinon depuis l'arborescence <root>/<type>/<brand>/<model>/."""
    labels = os.path.join(root, "labels.csv")
    samples = []
    if os.path.exists(labels):
        with open(labels, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if os.path.exists(r["file"]):
                    samples.append((r["file"], r["type"], r["brand"], r["model"]))
        if samples:
            return samples
    # repli : parcours de l'arborescence
    for dirpath, dirnames, _ in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != REJECTED_DIRNAME]
        for p in FileUtil.get_images_file_path_array(dirpath):
            rel = os.path.relpath(p, root).split(os.sep)
            if len(rel) >= 4:
                samples.append((p, rel[0], rel[1], rel[2]))
    return samples


def split_class(groups, val_r, test_r, rng):
    """groups = liste de listes d'images (doublons regroupés). Retourne un dict
    split -> images, en gardant chaque groupe entier et en visant les ratios."""
    n = sum(len(g) for g in groups)
    rng.shuffle(groups)
    if n < MIN_PER_CLASS:
        return {"train": [img for g in groups for img in g], "val": [], "test": []}, True

    t_test, t_val = round(n * test_r), round(n * val_r)
    out = {"train": [], "val": [], "test": []}
    for g in groups:
        if len(out["test"]) < t_test:
            out["test"].extend(g)
        elif len(out["val"]) < t_val:
            out["val"].extend(g)
        else:
            out["train"].extend(g)
    return out, False


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("dataset", nargs="?", default="dataset_moto")
    parser.add_argument("-val", type=float, default=0.15, help="Proportion validation (défaut 0.15)")
    parser.add_argument("-test", type=float, default=0.15, help="Proportion test (défaut 0.15)")
    parser.add_argument("-seed", type=int, default=42)
    parser.add_argument("-o", "--out", default=None, help="CSV de sortie (défaut <dataset>/dataset_split.csv)")
    args = parser.parse_args()

    rng = random.Random(args.seed)
    samples = read_samples(args.dataset)
    if not samples:
        raise SystemExit("Aucune image trouvée dans %s" % args.dataset)
    print("> %d image(s) trouvée(s)" % len(samples))

    # 1) hash perceptuel -> regroupement des quasi-doublons, par classe
    #    clé de groupe = (classe, dhash) : garde les doublons ensemble.
    groups_by_class = defaultdict(lambda: defaultdict(list))
    unreadable = 0
    for i, (path, t, b, m) in enumerate(samples, 1):
        cls = (t, b, m)
        try:
            with Image.open(path) as im:
                h = str(imagehash.dhash(im.convert("RGB")))
        except Exception:
            unreadable += 1
            continue
        groups_by_class[cls][h].append((path, t, b, m))
        if i % 200 == 0 or i == len(samples):
            print("\r  hachage %d/%d" % (i, len(samples)), end="", flush=True)
    print()

    # 2) découpage stratifié par classe
    rows, tiny = [], []
    counts = {"train": 0, "val": 0, "test": 0}
    dup_images = 0
    for cls, hmap in groups_by_class.items():
        groups = list(hmap.values())
        dup_images += sum(len(g) - 1 for g in groups)   # doublons perceptuels détectés
        assigned, is_tiny = split_class(groups, args.val, args.test, rng)
        if is_tiny:
            tiny.append(cls)
        for split, imgs in assigned.items():
            counts[split] += len(imgs)
            for (path, t, b, m) in imgs:
                rows.append([path, t, b, m, split])

    # 3) écriture du manifeste
    out = args.out or os.path.join(args.dataset, "dataset_split.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["file", "type", "brand", "model", "split"])
        w.writerows(rows)

    # 4) audit
    per_type = defaultdict(int)
    per_model = defaultdict(int)
    for (path, t, b, m, split) in rows:
        per_type[t] += 1
        per_model[(t, b, m)] += 1
    total = len(rows)
    print("\n=== AUDIT ===")
    print("images utilisables : %d   (illisibles ignorées : %d)" % (total, unreadable))
    print("quasi-doublons regroupés (anti-fuite) : %d" % dup_images)
    print("\npar type :")
    for t in sorted(per_type):
        print("  %-10s %5d  (%.0f%%)" % (t, per_type[t], 100 * per_type[t] / total))
    print("\nsplits :")
    for s in ("train", "val", "test"):
        print("  %-6s %5d  (%.0f%%)" % (s, counts[s], 100 * counts[s] / total))
    smallest = sorted(per_model.items(), key=lambda kv: kv[1])[:5]
    print("\n5 classes (modèle) les plus pauvres :")
    for (t, b, m), c in smallest:
        print("  %-8s %-14s %-16s %4d" % (t, b, m, c))
    if tiny:
        print("\n⚠ %d classe(s) trop petite(s) (<%d img) mise(s) entièrement en train : %s"
              % (len(tiny), MIN_PER_CLASS, ", ".join("/".join(c) for c in tiny[:5])
                 + (" …" if len(tiny) > 5 else "")))
    print("\n✓ manifeste écrit : %s" % out)


if __name__ == "__main__":
    main()
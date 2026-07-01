"""Nettoie un dataset d'images scrapées en ne gardant que les vraies motos.

Méthode : CLIP en zero-shot. Pour chaque image on compare une liste de
descriptions « positives » (moto) et « négatives » (personne, pièce, voiture,
logo, texte…). Si la meilleure description n'est pas une moto — ou si le score
est trop faible — l'image est DÉPLACÉE dans <dataset>/_rejected/ (jamais
supprimée). On régénère ensuite labels.csv à partir de ce qui reste.

Dépendances :
    pip install open_clip_torch torch pillow
GPU automatiquement utilisé si dispo ; sinon CPU (plus lent mais OK).

Exemples :
    python filter_dataset.py dataset_moto
    python filter_dataset.py dataset_moto -threshold 0.4 -device cuda
"""
import argparse
import csv
import os
import shutil

from utils.utils import FileUtil

REJECTED_DIRNAME = "_rejected"

POSITIVE_PROMPTS = [
    "a photo of a motorcycle",
    "a photo of a motorbike",
    "a side view of a parked motorcycle",
    "a motorcycle on a white background",
]
NEGATIVE_PROMPTS = [
    "a photo of a person",
    "a group of people",
    "a close-up of a motorcycle part",
    "a motorcycle engine close-up",
    "a motorcycle helmet",
    "a photo of a car",
    "a photo of a bicycle",
    "a screenshot of text",
    "a brand logo",
    "a spec sheet or brochure",
]


def iter_images(root: str):
    """Toutes les images du dataset, en ignorant le dossier _rejected."""
    for dirpath, dirnames, _ in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != REJECTED_DIRNAME]
        for p in FileUtil.get_images_file_path_array(dirpath):
            yield p


def reject(path: str, root: str):
    """Déplace `path` dans <root>/_rejected/ en conservant l'arborescence."""
    rel = os.path.relpath(path, root)
    dest = os.path.join(root, REJECTED_DIRNAME, rel)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if os.path.exists(dest):
        os.remove(path)
    else:
        shutil.move(path, dest)


def rebuild_labels(root: str) -> int:
    """Reconstruit labels.csv (file,type,brand,model) depuis l'arborescence
    <root>/<type>/<brand>/<model>/..., en ignorant _rejected."""
    labels_path = os.path.join(root, "labels.csv")
    n = 0
    with open(labels_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["file", "type", "brand", "model"])
        for path in iter_images(root):
            rel = os.path.relpath(path, root)
            parts = rel.split(os.sep)
            if len(parts) < 4:      # pas au niveau type/brand/model/fichier
                continue
            t, b, m = parts[0], parts[1], parts[2]
            w.writerow([path, t, b, m])
            n += 1
    return n


def build_scorer(device: str, threshold: float):
    """Retourne une fonction is_motorcycle(pil_image) -> bool, via CLIP."""
    import torch
    import open_clip

    model, _, preprocess = open_clip.create_model_and_transforms(
        "ViT-B-32", pretrained="laion2b_s34b_b79k")
    tokenizer = open_clip.get_tokenizer("ViT-B-32")
    model = model.to(device).eval()

    prompts = POSITIVE_PROMPTS + NEGATIVE_PROMPTS
    n_pos = len(POSITIVE_PROMPTS)
    with torch.no_grad():
        text = tokenizer(prompts).to(device)
        text_features = model.encode_text(text)
        text_features /= text_features.norm(dim=-1, keepdim=True)

    def is_motorcycle(pil_image) -> bool:
        with torch.no_grad():
            img = preprocess(pil_image).unsqueeze(0).to(device)
            feat = model.encode_image(img)
            feat /= feat.norm(dim=-1, keepdim=True)
            probs = (100.0 * feat @ text_features.T).softmax(dim=-1)[0]
        pos = float(probs[:n_pos].max())
        neg = float(probs[n_pos:].max())
        return pos >= neg and pos >= threshold

    return is_motorcycle


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("dataset", nargs="?", default="dataset_moto",
                        help="Dossier racine du dataset (défaut : dataset_moto)")
    parser.add_argument("-threshold", type=float, default=0.30,
                        help="Score minimal pour garder une image (défaut : 0.30). "
                             "Plus haut = plus strict (moins de bruit, plus de pertes).")
    parser.add_argument("-device", default=None,
                        help="cpu / cuda (auto-détecté par défaut)")
    args = parser.parse_args()

    from PIL import Image
    try:
        import torch
        device = args.device or ("cuda" if torch.cuda.is_available() else "cpu")
    except ImportError:
        raise SystemExit("Installe d'abord : pip install open_clip_torch torch pillow")

    print("> chargement de CLIP sur %s…" % device)
    is_motorcycle = build_scorer(device, args.threshold)

    paths = list(iter_images(args.dataset))
    print("> %d image(s) à analyser dans \"%s\"" % (len(paths), args.dataset))

    kept = rejected = errors = 0
    for i, path in enumerate(paths, 1):
        try:
            with Image.open(path) as im:
                ok = is_motorcycle(im.convert("RGB"))
        except Exception:
            reject(path, args.dataset)   # image illisible/corrompue -> rejetée
            errors += 1
            continue
        if ok:
            kept += 1
        else:
            reject(path, args.dataset)
            rejected += 1
        if i % 50 == 0 or i == len(paths):
            print("\r  %d/%d  (gardées %d, rejetées %d, illisibles %d)"
                  % (i, len(paths), kept, rejected, errors), end="", flush=True)

    print()
    n = rebuild_labels(args.dataset)
    print("✓ %d image(s) conservée(s), %d déplacée(s) dans %s/, labels.csv régénéré (%d lignes)"
          % (kept, rejected + errors, REJECTED_DIRNAME, n))


if __name__ == "__main__":
    main()

# Fichier généré par Claude.
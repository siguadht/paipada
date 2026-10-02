# Paipaida

[中文](README.md) · [English](README.en.md)

**Edit decor directly inside a real room image.**

Upload a room photo and generate a front view. Hover over or select furniture to replace, recolor, or remove it. Once the image is approved, explore a matching 2.5D concept. The workflow is designed for homeowners and interior designers working with clients.

![Approved Paipaida living room result](frontend/public/site/approved-front.webp)

> This is an approved demonstration result. Image quality still depends on the source photo, viewpoint, and model. A first attempt on an arbitrary room is not guaranteed to meet expectations.

## The workflow

| Start with a photo | Edit in the image | Explore the space |
| --- | --- | --- |
| Add a room photo, optional style reference, and optional furniture reference separately. | Replace, recolor, or remove recognized items. Move the product picker beside the image. | The 2.5D view corresponds to the approved front version. It illustrates placement; it is not a measured floor plan. |

![Approved furniture hover and replacement interface](frontend/public/site/approved-interaction.webp)

[Watch the 15-second prerecorded tour](frontend/public/site/approved-demo-tour.mp4) · [See the matching 2.5D view](frontend/public/site/approved-25d-ui.webp)

The video is an edit of approved imagery, actual product-interface screenshots, and the matching 2.5D page. **It is not a continuous screen recording or a claim about live generation reliability.**

## Implemented

- Invitation login, user-level data isolation, uploads, and project history.
- Single-room and multi-room projects with a shared style direction and room-specific versions.
- Front-view generation, feedback-based regeneration, decor replacement/recolor/removal, and version restore.
- Whole-item hover feedback for prepared layers and a movable picker next to selected furniture.
- A matching 2.5D concept after front-view approval. The local demonstration catalog contains 28 items in 9 categories.

## Run locally

```bash
cp .env.example .env
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In another terminal:

```bash
cd frontend
npm install
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api/v1 npm run dev
```

Studio: `http://127.0.0.1:3000/` · Website preview: `http://127.0.0.1:3000/website`

See the [development guide](DEVELOPMENT_GUIDE.md) for details and the [project status](docs/项目状态.md) for decisions and validation limits.

## Public release scope

This repository includes source, tests, configuration templates, text documentation, and selected approved demonstration media. Invitation codes, secrets, the local database, original room photos, and brand product images are excluded. Brand imagery is used only for local demonstration; redistribution permission has not been obtained. Use your own test photos, and keep `DEMO_PRODUCT_CATALOG=0` unless you provide your own product images. Production deployment is not complete.

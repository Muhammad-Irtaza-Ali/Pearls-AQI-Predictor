from __future__ import annotations

import uvicorn


def main() -> int:
    uvicorn.run("feature_pipeline.api.main:app", host="0.0.0.0", port=8000, reload=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

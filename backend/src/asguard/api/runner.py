"""Development entrypoint: uvicorn asguard.api.main:app"""

import uvicorn

from asguard.config import get_settings

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run("asguard.api.main:app", host=settings.host, port=settings.port, reload=False)

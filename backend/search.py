import json
import sys

from .cache import search_cache


def main():
    if len(sys.argv) != 2:
        print(
            json.dumps(
                {
                    "status": "error",
                    "error": (
                        "Usage: python -m backend.search "
                        "<participant-country-code>"
                    ),
                },
                ensure_ascii=False,
            )
        )
        return 1

    country_code = sys.argv[1]

    try:
        payload = search_cache(
            country_code
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "error",
                    "error": str(exc),
                },
                ensure_ascii=False,
            )
        )
        return 1

    print(
        json.dumps(
            payload,
            ensure_ascii=False,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

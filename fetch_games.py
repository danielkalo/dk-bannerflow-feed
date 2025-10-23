import csv, json, os, requests, random

API_URL  = "https://api.draftkings.com/ads/v1/ads/7341a429-d59e-11ee-945d-0ef9c4d3a02d.json"
GAMETYPE = "Slots"
USER = os.environ["DK_API_USERNAME"]
PASS = os.environ["DK_API_PASSWORD"]

def select_square_image(images):
    """
    Return the 'square' ImageName URL from Images.
    Fallbacks: any URL-like field in the first image dict, or empty string.
    """
    if isinstance(images, list) and images:
        # 1) exact 'square'
        for im in images:
            if isinstance(im, dict) and str(im.get("ImageKey", "")).lower() == "square":
                for k in ("ImageName", "Url", "URL", "url", "LargeUrl", "MainUrl"):
                    if im.get(k):
                        return str(im[k])
        # 2) fallback: first url-ish field from first dict
        for im in images:
            if isinstance(im, dict):
                for k in ("ImageName", "Url", "URL", "url", "LargeUrl", "MainUrl"):
                    if im.get(k):
                        return str(im[k])
        # 3) fallback: first string
        if isinstance(images[0], str):
            return images[0]
        return ""
    if isinstance(images, dict) and images:
        if str(images.get("ImageKey", "")).lower() == "square":
            for k in ("ImageName", "Url", "URL", "url", "LargeUrl", "MainUrl"):
                if images.get(k):
                    return str(images[k])
        for k in ("ImageName", "Url", "URL", "url", "LargeUrl", "MainUrl"):
            if images.get(k):
                return str(images[k])
        return ""
    if isinstance(images, str):
        return images
    return ""

def fetch(operator_code):
    r = requests.get(
        API_URL,
        params={"GameType": GAMETYPE, "Operator": operator_code},
        auth=(USER, PASS),
        timeout=180
    )
    r.raise_for_status()
    data = r.json().get("data", [])
    out = []
    seen = set()  # de-dup key per game

    for it in data:
        # --- ProviderId: KEEP ONLY 'DraftKings' (exclude DraftKings2, etc.) ---
        provider = str(it.get("ProviderId") or it.get("ContentProviderName") or "").strip()
        if provider.lower() != "draftkings":
            continue

        # --- De-dupe: prefer GameId; fallback to normalized GameName ---
        game_id = it.get("GameId") or it.get("Id") or it.get("id") or it.get("GameID")
        game_name = it.get("GameName") or it.get("Name") or it.get("Title") or ""
        dedupe_key = str(game_id) if game_id not in (None, "") else game_name.strip().lower()
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        # --- Operator code (DK/GNOG) ---
        op = it.get("Operator") or {}
        op_code = op.get("Code") if isinstance(op, dict) else None
        op_code = op_code or operator_code

        # --- Only the square image URL ---
        image_url = select_square_image(it.get("Images"))

        out.append({
            "GameName":      game_name,
            "GameTypeId":    it.get("GameTypeId") or GAMETYPE,
            "Images":        image_url,
            "Operator/Code": op_code,
            "ProviderId":    "DraftKings",   # keep exactly 'DraftKings'
        })

    # --- Randomize row order each run ---
    random.shuffle(out)
    return out

def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["GameName","GameTypeId","Images","Operator/Code","ProviderId"])
        w.writeheader()
        w.writerows(rows)

if __name__ == "__main__":
    write_csv("games_dk.csv",   fetch("DK"))
    write_csv("games_gnog.csv", fetch("GNOG"))

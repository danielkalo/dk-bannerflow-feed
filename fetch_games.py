import csv, json, os, requests, random

API_URL  = "https://api.draftkings.com/ads/v1/ads/7341a429-d59e-11ee-945d-0ef9c4d3a02d.json"
GAMETYPE = "Slots"
USER = os.environ["DK_API_USERNAME"]
PASS = os.environ["DK_API_PASSWORD"]

# ---------- helpers ----------

def select_square_image(images):
    """Return the 'square' ImageName/Url. Fallback to first URL-ish field, else empty."""
    if isinstance(images, list) and images:
        # 1) exact 'square'
        for im in images:
            if isinstance(im, dict) and str(im.get("ImageKey","")).lower() == "square":
                for k in ("ImageName","Url","URL","url","LargeUrl","MainUrl"):
                    if im.get(k):
                        return str(im[k])
        # 2) fallback: first dict url-ish
        for im in images:
            if isinstance(im, dict):
                for k in ("ImageName","Url","URL","url","LargeUrl","MainUrl"):
                    if im.get(k):
                        return str(im[k])
        # 3) fallback: first string
        if isinstance(images[0], str):
            return images[0]
        return ""
    if isinstance(images, dict) and images:
        if str(images.get("ImageKey","")).lower() == "square":
            for k in ("ImageName","Url","URL","url","LargeUrl","MainUrl"):
                if images.get(k):
                    return str(images[k])
        for k in ("ImageName","Url","URL","url","LargeUrl","MainUrl"):
            if images.get(k):
                return str(images[k])
        return ""
    if isinstance(images, str):
        return images
    return ""

def is_draftkings_provider(item) -> bool:
    provider = str(item.get("ProviderId") or item.get("ContentProviderName") or "").strip()
    return provider.lower() == "draftkings"

def is_nj(item) -> bool:
    # Accept Jurisdiction = 'NJ' (or 'New Jersey'), or JurisdictionId == 1
    j = item.get("Jurisdiction")
    if isinstance(j, str) and j.strip().lower() in {"nj","new jersey"}:
        return True
    jid = item.get("JurisdictionId")
    if jid is not None and str(jid).strip() == "1":
        return True
    return False

def is_mobile(item) -> bool:
    ct = item.get("ClientType") or item.get("ClientPlatform")
    return str(ct).strip().lower() == "mobile"

def stable_key(item) -> str:
    """Pick the most stable game identifier available; fallback to name."""
    for k in ["GameCode","Slug","SeoSlug","UrlSlug","ContentId","CanonicalGameId","BaseGameId","GameBaseId",
              "GameId","Id","id"]:
        v = item.get(k)
        if v not in (None, ""):
            return f"dk::{str(v).lower()}"
    name = (item.get("GameName") or item.get("Name") or item.get("Title") or "").strip().lower()
    return f"dk::name::{name}"

# ---------- main ----------

def fetch(operator_code: str):
    # Server-side filters the API supports
    r = requests.get(
        API_URL,
        params={"GameType": GAMETYPE, "Operator": operator_code},
        auth=(USER, PASS),
        timeout=180
    )
    r.raise_for_status()
    data = r.json().get("data", [])

    keep = {}
    stats = {"total": len(data), "non_dk_provider": 0, "not_nj": 0, "not_mobile": 0, "dupes": 0}

    for it in data:
        # 1) ProviderId must be exactly DraftKings
        if not is_draftkings_provider(it):
            stats["non_dk_provider"] += 1
            continue
        # 2) Only NJ (Jurisdiction 'NJ' or JurisdictionId == 1)
        if not is_nj(it):
            stats["not_nj"] += 1
            continue
        # 3) Only Mobile
        if not is_mobile(it):
            stats["not_mobile"] += 1
            continue

        key = stable_key(it)
        if key in keep:
            stats["dupes"] += 1
            continue  # keep only the first instance we saw

        # Operator code (DK/GNOG)
        op = it.get("Operator") or {}
        op_code = op.get("Code") if isinstance(op, dict) else None
        op_code = op_code or operator_code

        row = {
            "GameName":      it.get("GameName") or it.get("Name") or it.get("Title") or "",
            "GameTypeId":    it.get("GameTypeId") or GAMETYPE,
            "Images":        select_square_image(it.get("Images")),
            "Operator/Code": op_code,
            "ProviderId":    "DraftKings",
        }
        keep[key] = row

    rows = list(keep.values())
    random.shuffle(rows)  # randomize order each run
    print(f"{operator_code}: total={stats['total']} kept={len(rows)} "
          f"non_dk_provider={stats['non_dk_provider']} not_nj={stats['not_nj']} "
          f"not_mobile={stats['not_mobile']} dupes={stats['dupes']}")
    return rows

def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["GameName","GameTypeId","Images","Operator/Code","ProviderId"])
        w.writeheader()
        w.writerows(rows)

if __name__ == "__main__":
    write_csv("games_dk.csv",   fetch("DK"))
    write_csv("games_gnog.csv", fetch("GNOG"))

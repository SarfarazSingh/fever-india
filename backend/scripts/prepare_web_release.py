"""Prepare a frontend-only deployment with an explicit API and Vercel project.

Creates an isolated source directory; excludes secrets, build output and tooling.
"""

import argparse
import json
import shutil
from pathlib import Path
from urllib.parse import urlsplit


def prepare(api_origin: str, destination: Path, project_id: str, org_id: str):
    parsed = urlsplit(api_origin)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.path not in ["", "/"] or parsed.query or parsed.fragment:
        raise ValueError("Use a plain HTTPS API origin without credentials or a path")
    source = Path(__file__).resolve().parents[2] / "web"
    if destination.exists():
        raise ValueError("Use a new empty deployment directory")
    def ignore(directory, names):
        return [n for n in names if n in {"node_modules", "dist", ".git", ".vercel"} or (n.startswith(".env") and n != ".env.example") or n.endswith(".tsbuildinfo")]
    shutil.copytree(source, destination, ignore=ignore)
    path = destination / "vercel.json"
    data = json.loads(path.read_text())
    for rewrite in data["rewrites"]:
        rewrite["destination"] = rewrite["destination"].replace("https://REPLACE_WITH_API_HOST", api_origin.rstrip("/"))
    data["framework"] = "vite"
    data["installCommand"] = "npm ci"
    path.write_text(json.dumps(data, indent=2) + "\n")
    metadata = destination / ".vercel"
    metadata.mkdir(mode=0o700)
    (metadata / "project.json").write_text(json.dumps({"projectId": project_id, "orgId": org_id}) + "\n")
    print(f"Prepared frontend-only source at {destination}; API and project are explicit")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-origin", required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--org-id", required=True)
    args = parser.parse_args()
    prepare(args.api_origin, args.destination, args.project_id, args.org_id)

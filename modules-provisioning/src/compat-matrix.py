#!/usr/bin/env python3
"""Write the provisioning script of the modules of a Jahia release, and the compatibility matrix
of Jahia releases and Jahia modules behind it, as JSON.

A Jahia release is read from the provisioning YAML of its packs (core, additional and EE
modules): it gives each module the release ships, at its exact version.
A module is read from Nexus: maven-metadata.xml lists its released versions, and for each
version the jar manifest gives Jahia-Required-Version and Jahia-Depends, and the pom gives
the org.jahia dependencies. Only the manifest of a jar is downloaded, through HTTP ranges.
A JavaScript module is an npm .tgz, read from the jahia block of its package.json.
A module is a system module when its manifest states Jahia-Module-Type: system.
The store is read through the module list that Jahia's module manager reads; each release gets
the version of each store module that its module manager would offer.

The provisioning script lists the modules one release ships, as an installOrUpgradeBundle block
that Jahia's provisioning reads: at the versions the release ships (--versions shipped), or each
at the newest version the Store offers that release (--versions store).

Examples:
  compat-matrix.py --jahia 8.2.3.2 --store --provisioning modules.yml --versions store
  compat-matrix.py --jahia 8.2.3.2 --jahia 8.2.2.1   # two releases and every module they ship
  compat-matrix.py --jahia --store                    # every release, and every store module
  compat-matrix.py --module jcontent                  # every release of jcontent
  compat-matrix.py --module jcontent@3.5.0 --no-follow

Nexus credentials come from NEXUS_USERNAME and NEXUS_PASSWORD, and go to Nexus only.
Python 3.9+, standard library only.
"""

import argparse
import base64
import concurrent.futures
import datetime
import io
import json
import os
import re
import sys
import tarfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

NEXUS = "https://devtools.jahia.com/nexus/content"
PUBLIC_REPOSITORY = NEXUS + "/groups/public"
ENTERPRISE_REPOSITORY = NEXUS + "/groups/enterprise"
PACKS_GROUP = "org.jahia.packages"
PACKS = ("jahia-core-modules", "jahia-additional-modules", "jahia-ee-core-modules")
DEFAULT_MODULE_GROUP = "org.jahia.modules"
STORE_URL = "https://store.jahia.com/en/sites/private-app-store"
STORE_PROXY = "https://store.jahia.com/modules/mavenproxy/store"
CACHE_FORMAT = 6
MANIFEST_KEYS = ("Bundle-SymbolicName", "Bundle-Version", "Jahia-Required-Version", "Jahia-Depends",
                 "Jahia-Module-Type", "Jahia-Source-Control-Connection")


def log(message):
    print(message, file=sys.stderr, flush=True)


class Nexus:
    """Reads artifacts from a list of Maven repositories, the first that has the file wins."""

    def __init__(self, repositories, username=None, password=None, timeout=60):
        self.repositories = repositories
        self.timeout = timeout
        self.headers = {"User-Agent": "jahia-compat-matrix"}
        self.authorization = None
        if username and password:
            token = base64.b64encode(f"{username}:{password}".encode()).decode()
            self.authorization = "Basic " + token

    def _open(self, url, byte_range=None, attempts=3):
        headers = dict(self.headers)
        # The Nexus credentials go to Nexus only, never to the Store or its proxy.
        if self.authorization and url.startswith(NEXUS + "/"):
            headers["Authorization"] = self.authorization
        if byte_range:
            headers["Range"] = byte_range
        # A store package names itself with spaces ("package/Augmented Search").
        url = urllib.parse.quote(url, safe=":/?&=%@+~")
        for attempt in range(1, attempts + 1):
            try:
                return urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=self.timeout)
            except urllib.error.HTTPError as error:
                if error.code < 500 or attempt == attempts:
                    raise
            except (urllib.error.URLError, TimeoutError):
                if attempt == attempts:
                    raise
            time.sleep(2 * attempt)

    def _first(self, path, reader):
        """reader(url) on the first repository that serves path, or None when none does."""
        for repository in self.repositories:
            try:
                return reader(f"{repository}/{path}")
            except urllib.error.HTTPError as error:
                if error.code not in (401, 403, 404):
                    raise
        return None

    def get(self, path):
        """The bytes of path, or None when no repository has it."""
        def read(url):
            with self._open(url) as response:
                return response.read()
        return self._first(path, read)

    def get_text(self, path):
        data = self.get(path)
        return None if data is None else data.decode("utf-8", errors="replace")

    def get_text_all(self, path):
        """The text of path on each repository that serves it, in order."""
        texts = []
        for repository in self.repositories:
            try:
                with self._open(f"{repository}/{path}") as response:
                    texts.append(response.read().decode("utf-8", errors="replace"))
            except urllib.error.HTTPError as error:
                if error.code not in (401, 403, 404):
                    raise
        return texts

    def range_file(self, path, fallback_url=None):
        """A range file on the first repository that has path, else on fallback_url."""
        found = self._first(path, lambda url: HttpRangeFile(self, url)) if path else None
        if found is None and fallback_url:
            try:
                found = HttpRangeFile(self, fallback_url)
            except urllib.error.HTTPError as error:
                if error.code not in (401, 403, 404):
                    raise
        return found


class HttpRangeFile(io.RawIOBase):
    """A read-only, seekable file over HTTP ranges, so zipfile reads one entry of a remote jar."""

    BLOCK = 64 * 1024

    def __init__(self, nexus, url):
        super().__init__()
        self.nexus, self.url, self.position, self.blocks = nexus, url, 0, {}
        # Nexus mishandles a suffix range (bytes=-N), so the size comes first, then the tail of the
        # zip, where its central directory sits.
        with nexus._open(url, "bytes=0-0") as response:
            content_range = response.headers.get("Content-Range", "")
            if response.status == 200:
                # The server ignores ranges (the Store's proxy does), so the whole jar is the tail.
                self.tail = response.read()
                self.tail_start, self.size = 0, len(self.tail)
                return
        match = re.search(r"/(\d+)$", content_range)
        if not match:
            raise IOError(f"{url} serves no byte range")
        self.size = int(match.group(1))
        self.tail_start = max(0, self.size - self.BLOCK)
        with nexus._open(url, f"bytes={self.tail_start}-{self.size - 1}") as response:
            self.tail = response.read()

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.position

    def seek(self, offset, whence=io.SEEK_SET):
        base = {io.SEEK_SET: 0, io.SEEK_CUR: self.position, io.SEEK_END: self.size}[whence]
        self.position = max(0, base + offset)
        return self.position

    def _block(self, index):
        if index not in self.blocks:
            start = index * self.BLOCK
            end = min(start + self.BLOCK, self.size) - 1
            with self.nexus._open(self.url, f"bytes={start}-{end}") as response:
                self.blocks[index] = response.read()
        return self.blocks[index]

    def read(self, size=-1):
        if size is None or size < 0:
            size = self.size - self.position
        size = min(size, self.size - self.position)
        chunks = []
        while size > 0:
            if self.position >= self.tail_start:
                offset = self.position - self.tail_start
                chunk = self.tail[offset:offset + size]
            else:
                index, offset = divmod(self.position, self.BLOCK)
                chunk = self._block(index)[offset:offset + size]
                if self.position + len(chunk) > self.tail_start:
                    chunk = chunk[:self.tail_start - self.position]
            if not chunk:
                break
            chunks.append(chunk)
            self.position += len(chunk)
            size -= len(chunk)
        return b"".join(chunks)

    def read_all(self):
        """The whole file in one request: a gzip stream cannot be read by ranges."""
        if self.tail_start == 0:
            return self.tail
        with self.nexus._open(self.url) as response:
            return response.read()

    def readinto(self, buffer):
        data = self.read(len(buffer))
        buffer[:len(data)] = data
        return len(data)


def version_key(version):
    """A sort key close enough to Maven's ordering: numbers numerically, qualifiers before them."""
    key = []
    for token in re.findall(r"\d+|[A-Za-z]+", version):
        key.append((1, int(token), "") if token.isdigit() else (0, 0, token.lower()))
    return key


def artifact_path(group_id, artifact_id, version=None, file_name=None):
    path = group_id.replace(".", "/") + "/" + artifact_id
    if version:
        path += "/" + version
    if file_name:
        path += "/" + file_name
    return path


def released_versions(nexus, group_id, artifact_id):
    """The released versions of every repository, or None when no repository knows the artifact.

    The repositories are read all, not the first that answers: a group that holds an old copy of a
    module serves a maven-metadata.xml that stops years before the versions another group lists."""
    versions, found = set(), False
    for text in nexus.get_text_all(artifact_path(group_id, artifact_id, file_name="maven-metadata.xml")):
        found = True
        versions |= {node.text.strip() for node in ET.fromstring(text).iter("version") if node.text}
    if not found:
        return None
    return sorted((v for v in versions if not v.upper().endswith("SNAPSHOT")), key=version_key)


def parse_manifest(text):
    attributes, last = {}, None
    for line in text.replace("\r\n", "\n").split("\n"):
        if line.startswith(" ") and last:
            attributes[last] += line[1:]
        elif ":" in line:
            last, value = line.split(":", 1)
            attributes[last] = value.strip()
    return attributes


def split_top_level(value, separator=","):
    """Split on separator outside brackets, since a version range such as [1.0,2.0) holds a comma."""
    parts, depth, current = [], 0, ""
    for char in value:
        if char in "[(":
            depth += 1
        elif char in "])":
            depth -= 1
        if char == separator and depth == 0:
            parts.append(current)
            current = ""
        else:
            current += char
    parts.append(current)
    return [part.strip() for part in parts if part.strip()]


def parse_jahia_depends(value):
    """Jahia-Depends: name[=version or range][;optional], comma separated."""
    dependencies = []
    for entry in split_top_level(value or ""):
        name, _, rest = entry.partition("=")
        name, _, flags = name.partition(";")
        version, _, version_flags = rest.partition(";")
        flags = [f.strip() for f in (flags + ";" + version_flags).split(";") if f.strip()]
        dependency = {"module": name.strip()}
        if version.strip():
            dependency["version"] = version.strip()
        if "optional" in flags:
            dependency["optional"] = True
        dependencies.append(dependency)
    return dependencies


class Poms:
    """Reads poms and resolves the version of their dependencies through the parent chain."""

    NS = re.compile(r"^\{[^}]*\}")

    def __init__(self, nexus):
        self.nexus = nexus
        self.cache = {}
        self.lock = threading.Lock()

    @classmethod
    def _strip(cls, element):
        for node in element.iter():
            if isinstance(node.tag, str):
                node.tag = cls.NS.sub("", node.tag)
        return element

    def load(self, group_id, artifact_id, version):
        key = (group_id, artifact_id, version)
        with self.lock:
            if key in self.cache:
                return self.cache[key]
        text = self.nexus.get_text(artifact_path(group_id, artifact_id, version, f"{artifact_id}-{version}.pom"))
        model = None
        if text is not None:
            model = self._model(self._strip(ET.fromstring(text.encode("utf-8"))))
        with self.lock:
            self.cache[key] = model
        return model

    def _model(self, root):
        def text(element, name):
            node = element.find(name) if element is not None else None
            return node.text.strip() if node is not None and node.text else None

        parent = root.find("parent")
        model = {
            "groupId": text(root, "groupId") or text(parent, "groupId"),
            "artifactId": text(root, "artifactId"),
            "version": text(root, "version") or text(parent, "version"),
            "packaging": text(root, "packaging") or "jar",
            "parent": None,
            "properties": {},
            "dependencies": [],
            "managed": {},
        }
        if parent is not None:
            model["parent"] = (text(parent, "groupId"), text(parent, "artifactId"), text(parent, "version"))
        properties = root.find("properties")
        if properties is not None:
            for node in properties:
                if isinstance(node.tag, str):
                    model["properties"][node.tag] = (node.text or "").strip()
        for node in root.findall("dependencyManagement/dependencies/dependency"):
            model["managed"][(text(node, "groupId"), text(node, "artifactId"))] = {
                "version": text(node, "version"), "scope": text(node, "scope")}
        for node in root.findall("dependencies/dependency"):
            model["dependencies"].append({
                "groupId": text(node, "groupId"), "artifactId": text(node, "artifactId"),
                "version": text(node, "version"), "scope": text(node, "scope"),
                "type": text(node, "type"), "optional": text(node, "optional") == "true"})
        return model

    def chain(self, model):
        """The model and its parents, nearest first."""
        chain, seen = [model], set()
        while chain[-1]["parent"] and chain[-1]["parent"] not in seen:
            seen.add(chain[-1]["parent"])
            parent = self.load(*chain[-1]["parent"])
            if parent is None:
                break
            chain.append(parent)
        return chain

    @staticmethod
    def interpolate(value, chain):
        if not value:
            return value
        project = chain[0]
        builtins = {"project.version": project["version"], "project.groupId": project["groupId"],
                    "project.artifactId": project["artifactId"], "pom.version": project["version"]}
        if project["parent"]:
            builtins["project.parent.version"] = project["parent"][2]
        for _ in range(10):
            def replace(match):
                name = match.group(1)
                if name in builtins:
                    return builtins[name]
                for model in chain:
                    if name in model["properties"]:
                        return model["properties"][name]
                return match.group(0)
            resolved = re.sub(r"\$\{([^}]+)\}", replace, value)
            if resolved == value:
                break
            value = resolved
        return value

    def jahia_dependencies(self, group_id, artifact_id, version):
        model = self.load(group_id, artifact_id, version)
        if model is None:
            return None, None
        chain = self.chain(model)
        # A pom names a coordinate either literally or through ${project.groupId}, and a managed
        # dependency and its use need not agree, so both sides are interpolated before they meet.
        managed = {}
        for ancestor in reversed(chain):
            for (group, artifact), management in ancestor["managed"].items():
                managed[(self.interpolate(group, chain), self.interpolate(artifact, chain))] = management
        dependencies = []
        for dependency in model["dependencies"]:
            dependency_group = self.interpolate(dependency["groupId"], chain) or ""
            if not dependency_group.startswith("org.jahia"):
                continue
            artifact = self.interpolate(dependency["artifactId"], chain)
            management = managed.get((dependency_group, artifact), {})
            entry = {"groupId": dependency_group, "artifactId": artifact,
                     "version": self.interpolate(dependency["version"] or management.get("version"), chain),
                     "scope": dependency["scope"] or management.get("scope") or "compile"}
            if dependency["type"] and dependency["type"] != "jar":
                entry["type"] = dependency["type"]
            if dependency["optional"]:
                entry["optional"] = True
            dependencies.append(entry)
        parent = None
        if model["parent"]:
            parent = dict(zip(("groupId", "artifactId", "version"), model["parent"]))
        return dependencies, parent


PROVISIONING_URL = re.compile(r"""url:\s*['"]?(js:)?mvn:([^/'"\s]+)/([^/'"\s]+)/([^/'"\s]+)""")
PROVISIONING_START_LEVEL = re.compile(r"startLevel:\s*(\d+)")


def parse_provisioning(text, pack):
    """The modules of a pack's provisioning YAML: an url line opens a module, and a startLevel line
    under it belongs to it. A JavaScript module is a js:mvn: url, which ends in /tgz."""
    modules = []
    for line in text.splitlines():
        match = PROVISIONING_URL.search(line)
        if match:
            js, group_id, artifact_id, version = match.groups()
            module = {"groupId": group_id, "artifactId": artifact_id, "version": version, "pack": pack}
            if js:
                module["type"] = "js"
            modules.append(module)
            continue
        match = PROVISIONING_START_LEVEL.search(line)
        if match and modules:
            modules[-1]["startLevel"] = int(match.group(1))
    return modules


def read_release(nexus, version):
    release = {"packs": {}, "modules": []}
    for pack in PACKS:
        file_name = f"{pack}-{version}-provisioning.yaml"
        text = nexus.get_text(artifact_path(PACKS_GROUP, pack, version, file_name))
        if text is None:
            release["packs"][pack] = None
            continue
        modules = parse_provisioning(text, pack)
        release["packs"][pack] = len(modules)
        release["modules"].extend(modules)
    release["modules"].sort(key=lambda m: (m["artifactId"], m["groupId"]))
    return release


def read_java_module(archive_file, entry):
    with zipfile.ZipFile(io.BufferedReader(archive_file, buffer_size=HttpRangeFile.BLOCK)) as archive:
        manifest = parse_manifest(archive.read("META-INF/MANIFEST.MF").decode("utf-8", errors="replace"))
    entry["packaging"] = "jar"
    entry["moduleType"] = manifest.get("Jahia-Module-Type")
    entry["jahiaRequiredVersion"] = manifest.get("Jahia-Required-Version")
    entry["jahiaDepends"] = parse_jahia_depends(manifest.get("Jahia-Depends"))
    entry["manifest"] = {key: manifest[key] for key in MANIFEST_KEYS if key in manifest}


def read_javascript_module(archive_file, entry):
    """A JavaScript module is an npm package: its package.json holds the Jahia metadata."""
    with tarfile.open(fileobj=io.BytesIO(archive_file.read_all()), mode="r:gz") as archive:
        member = next(m for m in archive.getmembers() if m.name.lstrip("./") == "package/package.json")
        package = json.load(archive.extractfile(member))
    jahia = package.get("jahia") or {}
    entry["packaging"] = "tgz"
    entry["moduleType"] = jahia.get("module-type")
    entry["jahiaRequiredVersion"] = jahia.get("required-version")
    entry["jahiaDepends"] = parse_jahia_depends(jahia.get("module-dependencies"))
    entry["packageJson"] = {"name": package.get("name"), "version": package.get("version"),
                            "jahia": {k: v for k, v in jahia.items() if k != "maven"}}


def read_module_version(nexus, poms, group_id, artifact_id, version, jar_url=None):
    entry = {}
    try:
        archive_file = None
        for extension in ("jar", "tgz"):
            path = artifact_path(group_id, artifact_id, version, f"{artifact_id}-{version}.{extension}")
            archive_file = nexus.range_file(path)
            if archive_file is not None:
                break
        if archive_file is None and jar_url:
            archive_file = nexus.range_file(None, jar_url)
        if archive_file is None:
            model = poms.load(group_id, artifact_id, version)
            if model is not None and model["packaging"] not in ("jar", "bundle"):
                # A pom-only artifact, such as the library Maven wraps for JavaScript modules, or
                # the war of a Jahia 6 module, which has no manifest to read.
                entry["packaging"] = model["packaging"]
            else:
                entry["error"] = "no jar"
        elif archive_file.read(2) == b"\x1f\x8b":
            read_javascript_module(archive_file, entry)
        else:
            archive_file.seek(0)
            read_java_module(archive_file, entry)
        dependencies, parent = poms.jahia_dependencies(group_id, artifact_id, version)
        if dependencies is None:
            # An npm package has no pom by design, so only a jar is in error without one.
            if entry.get("packaging") != "tgz":
                entry.setdefault("error", "no pom")
        else:
            entry["parent"] = parent
            entry["mavenDependencies"] = dependencies
    except (urllib.error.URLError, OSError) as error:
        # A network failure is transient: the entry stays out of the cache and the next run retries it.
        return {"error": f"{type(error).__name__}: {error}", "transient": True}
    except (zipfile.BadZipFile, tarfile.TarError, StopIteration, KeyError, ValueError, ET.ParseError) as error:
        entry["error"] = f"{type(error).__name__}: {error}"
    return entry


def read_store(nexus, url):
    """The module list that Jahia's module manager reads from a store (ForgeService)."""
    with nexus._open(url.rstrip("/") + "/contents/modules-repository.moduleList.json") as response:
        repositories = json.loads(response.read().decode("utf-8"))
    store = {}
    for module in repositories[0]["modules"]:
        key = f"{module['groupId']}:{module['name']}"
        store[key] = {
            "groupId": module["groupId"], "artifactId": module["name"],
            "title": module.get("title"), "status": module.get("status"),
            "versions": {v["version"]: {"requiredVersion": v["requiredVersion"].replace("version-", "", 1),
                                        "downloadUrl": v.get("downloadUrl")}
                         for v in module.get("versions", [])},
        }
    return store


def store_offer(store_module, jahia_version):
    """The version the module manager of jahia_version offers: the newest one whose required version
    is at most jahia_version, on the same major."""
    jahia = version_key(jahia_version)
    offered = [v for v, data in store_module["versions"].items()
               if version_key(data["requiredVersion"]) <= jahia
               and version_key(data["requiredVersion"])[:1] == jahia[:1]]
    return max(offered, key=version_key) if offered else None


def parse_coordinate(value, default_group):
    """artifactId, groupId:artifactId, either with @version."""
    coordinate, _, version = value.partition("@")
    group_id, _, artifact_id = coordinate.rpartition(":")
    return group_id or default_group, artifact_id, version or None


def load_cache(path):
    if not path or not os.path.exists(path):
        return {"format": CACHE_FORMAT, "versions": {}, "releases": {}}
    with open(path, encoding="utf-8") as handle:
        cache = json.load(handle)
    if cache.get("format") != CACHE_FORMAT:
        return {"format": CACHE_FORMAT, "versions": {}, "releases": {}}
    return cache


def save_json(path, data):
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=False)
        handle.write("\n")
    os.replace(temporary, path)


class Matrix:
    def __init__(self, nexus, cache, jobs, follow):
        self.nexus, self.cache, self.jobs, self.follow = nexus, cache, jobs, follow
        self.poms = Poms(nexus)
        self.releases = {}
        self.modules = {}
        self.queued = set()
        self.pending = []
        self.store = None
        self.lock = threading.Lock()

    def add_store(self, store, read_modules=True):
        """Know the Store, and read every module of it unless read_modules is False, as a
        provisioning script needs the offers of the Store but not the matrix of its modules."""
        self.store = store
        if read_modules:
            for module in store.values():
                self.queue(module["groupId"], module["artifactId"])

    def _store_jar(self, key, version):
        module = (self.store or {}).get(key)
        return ((module or {}).get("versions", {}).get(version) or {}).get("downloadUrl")

    def add_release(self, version):
        release = self.cache["releases"].get(version)
        if release is None:
            log(f"release {version}: reading the provisioning of its packs")
            release = read_release(self.nexus, version)
            if any(release["packs"].values()):
                self.cache["releases"][version] = release
        self.releases[version] = release
        if not any(release["packs"].values()):
            log(f"release {version}: no pack found on Nexus")
        return release

    def queue(self, group_id, artifact_id, versions=None):
        key = f"{group_id}:{artifact_id}"
        with self.lock:
            if key in self.queued and versions is None:
                return
            self.queued.add(key)
        self.pending.append((group_id, artifact_id, versions))

    def run(self):
        """Read the queued modules, then the modules they depend on, one wave at a time."""
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.jobs) as pool:
            while self.pending:
                batch, self.pending = self.pending, []
                listed = list(pool.map(lambda item: self._versions_of(*item), batch))
                tasks = {}
                for (group_id, artifact_id, _), versions in zip(batch, listed):
                    key = f"{group_id}:{artifact_id}"
                    for version in versions or []:
                        if f"{key}:{version}" in self.cache["versions"]:
                            self.modules[key]["versions"][version] = self.cache["versions"][f"{key}:{version}"]
                        else:
                            tasks[pool.submit(read_module_version, self.nexus, self.poms, group_id,
                                              artifact_id, version, self._store_jar(key, version))] = (key, version)
                log(f"wave of {len(batch)} modules: {len(tasks)} versions to read")
                for future in concurrent.futures.as_completed(tasks):
                    key, version = tasks[future]
                    entry = future.result()
                    if not entry.get("transient"):
                        self.cache["versions"][f"{key}:{version}"] = entry
                    self.modules[key]["versions"][version] = entry
                for group_id, artifact_id, _ in batch:
                    self._sort_and_follow(f"{group_id}:{artifact_id}", group_id)

    def _versions_of(self, group_id, artifact_id, versions):
        key = f"{group_id}:{artifact_id}"
        with self.lock:
            module = self.modules.setdefault(key, {"groupId": group_id, "artifactId": artifact_id,
                                                   "versions": {}})
        if versions is not None:
            return versions
        try:
            listed = released_versions(self.nexus, group_id, artifact_id)
        except (urllib.error.URLError, OSError, ValueError, ET.ParseError) as error:
            log(f"module {key}: maven-metadata.xml unreadable, {type(error).__name__}: {error}")
            listed = None
        in_store = list((self.store or {}).get(key, {}).get("versions", {}))
        # A version a release pins exists, whether or not a maven-metadata.xml lists it.
        pinned = {module["version"] for release in self.releases.values() for module in release["modules"]
                  if f"{module['groupId']}:{module['artifactId']}" == key
                  and not module["version"].upper().endswith("SNAPSHOT")}
        if listed is None and not in_store and not pinned:
            module["error"] = "no maven-metadata.xml"
            log(f"module {key}: not found on Nexus")
            return None
        return sorted(set(listed or []) | set(in_store) | pinned, key=version_key)

    def _sort_and_follow(self, key, group_id):
        module = self.modules[key]
        module["versions"] = dict(sorted(module["versions"].items(), key=lambda item: version_key(item[0])))
        if not self.follow:
            return
        for entry in module["versions"].values():
            for dependency in (entry or {}).get("jahiaDepends", []):
                self.queue(self._group_of(dependency["module"], group_id), dependency["module"])
            for dependency in (entry or {}).get("mavenDependencies", []):
                if dependency["groupId"] == DEFAULT_MODULE_GROUP:
                    self.queue(dependency["groupId"], dependency["artifactId"])

    def _group_of(self, artifact_id, fallback):
        """Jahia-Depends names a module without its groupId: take the one a release or a pom gives."""
        for release in self.releases.values():
            for module in release["modules"]:
                if module["artifactId"] == artifact_id:
                    return module["groupId"]
        for key in self.modules:
            group_id, _, known = key.rpartition(":")
            if known == artifact_id:
                return group_id
        return DEFAULT_MODULE_GROUP if fallback.startswith("org.jahia") else fallback

    def document(self, repositories, store_url):
        for module in self.modules.values():
            types = [e.get("moduleType") or (e.get("manifest") or {}).get("Jahia-Module-Type")
                     for e in module["versions"].values() if e]
            types = [t for t in types if t]
            # The newest version that states a type decides it.
            module["moduleType"] = types[-1] if types else None
            module["system"] = module["moduleType"] == "system"
        releases = {}
        for version, release in sorted(self.releases.items(), key=lambda item: version_key(item[0])):
            release = dict(release)
            if self.store is not None:
                offers = {key: store_offer(module, version) for key, module in sorted(self.store.items())}
                release["storeOffers"] = {key: offer for key, offer in offers.items() if offer}
            releases[version] = release
        document = {
            "generatedAt": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "repositories": repositories,
            "jahia": releases,
            "modules": dict(sorted(self.modules.items())),
        }
        if self.store is not None:
            document["store"] = {"url": store_url, "modules": dict(sorted(self.store.items()))}
        return document


def provisioning_modules(document, jahia_version, versions):
    """The modules of the provisioning script of a release: each module the release ships, at its
    shipped version, or at the newest version the Store offers that release when versions is store
    and the Store lists the module. A module absent from the Store keeps its shipped version."""
    release = document["jahia"][jahia_version]
    offers = release.get("storeOffers", {})
    modules = []
    for shipped in release["modules"]:
        key = f"{shipped['groupId']}:{shipped['artifactId']}"
        module = dict(shipped)
        module["shippedVersion"] = shipped["version"]
        if versions == "store" and key in offers:
            module["version"] = offers[key]
        entry = document["modules"].get(key, {}).get("versions", {}).get(module["version"]) or {}
        if entry.get("packaging") == "tgz":
            module["type"] = "js"
        modules.append(module)
    return modules


def write_provisioning(path, document, jahia_version, versions, store_url):
    modules = provisioning_modules(document, jahia_version, versions)
    upgraded = [m for m in modules if m["version"] != m["shippedVersion"]]
    lines = [f"# Jahia {jahia_version}: the {len(modules)} modules it ships, each at "
             + ("the newest version the Store offers that release." if versions == "store"
                else "the version it ships.")]
    if versions == "store":
        lines.append(f"# {len(upgraded)} of them are newer than shipped. Store: {store_url}")
    lines.append(f"# Generated on {document['generatedAt']} by jahia-modules-action/modules-provisioning.")
    lines.append("- installOrUpgradeBundle:")
    for module in modules:
        if module.get("type") == "js":
            url = f"js:mvn:{module['groupId']}/{module['artifactId']}/{module['version']}/tgz"
        else:
            url = f"mvn:{module['groupId']}/{module['artifactId']}/{module['version']}"
        comment = f"  # shipped {module['shippedVersion']}" if module["version"] != module["shippedVersion"] else ""
        lines.append(f"    - url: '{url}'{comment}")
        if "startLevel" in module:
            lines.append(f"      startLevel: {module['startLevel']}")
    lines.append("  autoStart: true")
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    return modules, upgraded


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--jahia", action="append", nargs="?", const="", metavar="VERSION",
                        help="a Jahia release, repeatable or comma separated; with no value, every release")
    parser.add_argument("--module", action="append", metavar="[GROUP:]ARTIFACT[@VERSION]",
                        help="a module, repeatable; with no version, every released version")
    parser.add_argument("--no-follow", action="store_true",
                        help="do not read the modules that Jahia-Depends and the pom name")
    parser.add_argument("--release-modules", choices=("shipped", "all"), default="all",
                        help="for a release: read every version of its modules (all), or the shipped one only")
    parser.add_argument("--output", default="compat-matrix.json", help="the JSON matrix")
    parser.add_argument("--provisioning", metavar="PATH",
                        help="write the provisioning script of the one --jahia release to PATH")
    parser.add_argument("--versions", choices=("shipped", "store"), default="shipped",
                        help="the version of each module of the provisioning script: the one the release "
                             "ships, or the newest the Store offers that release (needs --store)")
    parser.add_argument("--cache", help="a JSON cache of released versions, which never change")
    parser.add_argument("--repository", action="append",
                        help="a Maven repository URL, repeatable, tried in order")
    parser.add_argument("--store", nargs="?", const=STORE_URL, metavar="URL",
                        help=f"also read every module of a store, and what it offers each release (default {STORE_URL})")
    parser.add_argument("--jobs", type=int, default=8)
    args = parser.parse_args(argv)
    if not args.jahia and not args.module and not args.store:
        parser.error("name at least one --jahia, --module or --store")
    if args.versions == "store" and not args.store:
        parser.error("--versions store needs --store")

    username, password = os.environ.get("NEXUS_USERNAME"), os.environ.get("NEXUS_PASSWORD")
    repositories = args.repository or ([ENTERPRISE_REPOSITORY, PUBLIC_REPOSITORY] if username and password
                                       else [PUBLIC_REPOSITORY])
    if args.store and STORE_PROXY not in repositories:
        # The Store serves the modules Nexus lacks, the community ones, through its Maven proxy.
        repositories = repositories + [STORE_PROXY]
    nexus = Nexus(repositories, username, password)
    cache = load_cache(args.cache)
    matrix = Matrix(nexus, cache, args.jobs, follow=not args.no_follow)
    if args.store:
        store = read_store(nexus, args.store)
        log(f"store {args.store}: {len(store)} modules")
        matrix.add_store(store, read_modules=not args.provisioning)

    jahia_versions = []
    for value in args.jahia or []:
        if value == "":
            listed = released_versions(nexus, PACKS_GROUP, PACKS[0]) or []
            log(f"{len(listed)} Jahia releases published on Nexus")
            jahia_versions.extend(listed)
        else:
            jahia_versions.extend(v.strip() for v in value.split(",") if v.strip())
    jahia_versions = list(dict.fromkeys(jahia_versions))
    if args.provisioning and len(jahia_versions) != 1:
        parser.error("--provisioning writes the script of one --jahia release")
    for version in jahia_versions:
        for module in matrix.add_release(version)["modules"]:
            shipped = [module["version"]] if args.release_modules == "shipped" else None
            matrix.queue(module["groupId"], module["artifactId"], shipped)
    for value in args.module or []:
        group_id, artifact_id, version = parse_coordinate(value, DEFAULT_MODULE_GROUP)
        matrix.queue(group_id, artifact_id, [version] if version else None)
    if args.provisioning and args.versions == "store":
        # The Store's offer of a shipped module is read too, so its packaging names the url to write.
        release = matrix.releases[jahia_versions[0]]
        for module in release["modules"]:
            key = f"{module['groupId']}:{module['artifactId']}"
            offer = store_offer(store[key], jahia_versions[0]) if key in store else None
            if offer and offer != module["version"]:
                matrix.queue(module["groupId"], module["artifactId"], [offer])

    matrix.run()
    document = matrix.document(repositories, args.store)
    save_json(args.output, document)
    if args.cache:
        save_json(args.cache, cache)
    entries = [e for m in matrix.modules.values() for e in m["versions"].values()]
    errors = sum(1 for e in entries if "error" in e)
    transient = sum(1 for e in entries if e.get("transient"))
    log(f"wrote {args.output}: {len(matrix.releases)} releases, {len(matrix.modules)} modules, "
        f"{len(entries)} versions, {errors} in error ({transient} network failures)")
    if args.provisioning:
        release = matrix.releases[jahia_versions[0]]
        if not any(release["packs"].values()):
            log(f"no provisioning script: Jahia {jahia_versions[0]} has no pack on Nexus")
            return 1
        modules, upgraded = write_provisioning(args.provisioning, document, jahia_versions[0],
                                               args.versions, args.store)
        log(f"wrote {args.provisioning}: {len(modules)} modules of Jahia {jahia_versions[0]}, "
            f"{len(upgraded)} newer than shipped")
    return 1 if transient else 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import logging
import pathlib
import re
import shutil
import statistics
import sys
import tempfile
from typing import Dict, List, NamedTuple, Optional, Set, Tuple, TypeVar

__version__ = "0.2.0"


logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger("prepropress_cancellation")

shapely = None
try:
    import shapely.geometry
except ImportError:
    logger.info("Shapely not found, complex hulls disabled")
except OSError:
    logger.exception("Failed to import shapely. Are you missing libgeos?")

HEADER_MARKER = f"; Pre-Processed for Cancel-Object support by preprocess_cancellation v{__version__}\n"


PathLike = TypeVar("PathLike", str, pathlib.Path)


class Point(NamedTuple):
    x: float
    y: float


class HullTracker:
    def add_point(self, point: Point):
        ...

    def center(self) -> Point:
        ...

    def exterior(self) -> list[Point]:
        ...

    @classmethod
    def create(cls):
        if shapely:
            return ShapelyHullTracker()
        return SimpleHullTracker()


class SimpleHullTracker(HullTracker):
    def __init__(self) -> None:
        self.xmin = 999999
        self.ymin = 999999
        self.xmax = -999999
        self.ymax = -999999

        self.count_points = 0
        self.xsum = 0
        self.ysum = 0

    def add_point(self, point: Point):
        self.xsum += point.x
        self.ysum += point.y
        self.count_points += 1

        if point.x < self.xmin:
            self.xmin = point.x
        if point.y < self.ymin:
            self.ymin = point.y
        if point.x > self.xmax:
            self.xmax = point.x
        if point.y > self.ymax:
            self.ymax = point.y

    def center(self):
        if not self.count_points:
            return

        return Point(
            self.xsum / self.count_points,
            self.ysum / self.count_points,
        )

    def exterior(self):
        if not self.count_points:
            return

        return boundingbox((self.xmin, self.ymin), (self.xmax, self.ymax))


class ShapelyHullTracker(HullTracker):
    def __init__(self):
        self.pos = None
        self.points: Set[Point] = set()

    def add_point(self, point: Point):
        self.points.add(point)

    def center(self):
        if not self.points:
            return

        return Point(
            statistics.mean(p[0] for p in self.points),
            statistics.mean(p[1] for p in self.points),
        )

    def exterior(self):
        if not self.points:
            return

        return list(
            shapely.geometry.MultiPoint(list(self.points))
            .convex_hull.simplify(0.02, preserve_topology=False)
            .exterior.coords
        )


class KnownObject(NamedTuple):
    name: str
    hull: HullTracker


def boundingbox(pmin: Point, pmax: Point):
    return [
        (pmin[0], pmin[1]),
        (pmin[0], pmax[1]),
        (pmax[0], pmax[1]),
        (pmax[0], pmin[1]),
    ]


def _dump_coords(coords: List[float]) -> str:
    return ",".join(map("{:0.3f}".format, coords))


def _clean_id(id):
    return re.sub(r"\W+", "_", id).strip("_")


def parse_gcode(line):
    # drop comments
    line = line.split(";", maxsplit=1)[0]
    command, *params = line.strip().split()
    parsed = {}
    for param in params:
        if "=" in param:
            parsed.update(dict(zip(param.split("=", maxsplit=1))))
        else:
            parsed.update({param[0].upper(): param[1:]})
    return command, parsed


def header(object_count):
    yield "\n\n"
    yield HEADER_MARKER
    yield f"; {object_count} known objects\n"


def define_object(
    name,
    center: Optional[Point] = None,
    polygon: Optional[Point] = None,
    region: Optional[List[Point]] = None,
):
    yield f"EXCLUDE_OBJECT_DEFINE NAME={name}"
    if center:
        yield f" CENTER={_dump_coords(center)}"
    if polygon:
        yield f" POLYGON={json.dumps(polygon, separators=(',', ':'))}"
    if region:
        yield f" REGION={_dump_coords(region, separators=(',', ':'))}"
    yield "\n"


def object_start_marker(object_name):
    yield f"EXCLUDE_OBJECT_START NAME={object_name}\n"


def object_end_marker(object_name):
    yield f"EXCLUDE_OBJECT_END NAME={object_name}\n"


def preprocess_pipe(infile):
    yield from infile


def preprocess_m486(infile):
    known_objects: Dict[str, KnownObject] = {}
    current_hull: Optional[HullTracker] = None

    for line in infile:

        if line.startswith("M486"):
            _, params = parse_gcode(line)
            if "T" in params:
                for i in range(-1, int(params["T"])):
                    known_objects[f"{i}"] = KnownObject(f"{i}", HullTracker.create())

            elif "S" in params:
                current_hull = known_objects[params["S"]].hull

        if current_hull and line.strip().lower().startswith("g"):
            _, params = parse_gcode(line)
            if float(params.get("E", -1)) > 0 and "X" in params and "Y" in params:
                x = float(params["X"])
                y = float(params["Y"])
                current_hull.add_point(Point(x, y))

    infile.seek(0)
    current_object = None
    for line in infile:
        if line.upper().startswith("M486"):
            _, params = parse_gcode(line)

            if "T" in params:
                # Inject custom marker
                yield from header(len(known_objects))
                for mesh_id, hull in known_objects.values():
                    if mesh_id == "-1":
                        continue

                    yield from define_object(
                        mesh_id,
                        center=hull.center(),
                        polygon=hull.exterior(),
                    )

            if "S" in params:
                if current_object:
                    yield from object_end_marker(current_object.name)
                    current_object = None

                if params["S"] != "-1":
                    current_object = known_objects[params["S"]]
                    yield from object_start_marker(current_object.name)

            yield "; "  # Comment out the original M486 lines

        yield line


def preprocess_cura(infile):
    known_objects: Dict[str, KnownObject] = {}
    current_hull: Optional[HullTracker] = None
    last_time_elapsed: str = None

    # iterate the file twice, to be able to inject the header markers
    for line in infile:
        if line.startswith(";MESH:"):
            object_name = line.split(":", maxsplit=1)[1].strip()
            if object_name == "NONMESH":
                continue
            if object_name not in known_objects:
                known_objects[object_name] = KnownObject(_clean_id(object_name), HullTracker.create())
            current_hull = known_objects[object_name].hull

        if current_hull and line.strip().lower().startswith("g"):
            _, params = parse_gcode(line)
            if float(params.get("E", -1)) > 0 and "X" in params and "Y" in params:
                x = float(params["X"])
                y = float(params["Y"])
                current_hull.add_point(Point(x, y))

        if line.startswith(";TIME_ELAPSED:"):
            last_time_elapsed = line

    infile.seek(0)
    for line in infile:
        if line.strip() and not line.startswith(";"):
            # Inject custom marker
            yield from header(len(known_objects))
            for mesh_id, hull in known_objects.values():
                yield from define_object(
                    mesh_id,
                    center=hull.center(),
                    polygon=hull.exterior(),
                )
            yield line
            break
        yield line

    current_object = None
    for line in infile:
        yield line

        if line.startswith(";MESH:"):
            if current_object:
                yield from object_end_marker(current_object)
                current_object = None
            mesh = line.split(":", maxsplit=1)[1].strip()
            if mesh == "NONMESH":
                continue
            current_object, _ = known_objects[mesh]
            yield from object_start_marker(current_object)

        if line == last_time_elapsed and current_object:
            yield from object_end_marker(current_object)
            current_object = None

    if current_object:
        yield from object_end_marker(current_object)


def preprocess_slicer(infile):
    known_objects: Dict[str, KnownObject] = {}
    current_hull: Optional[HullTracker] = None
    for line in infile:
        if line.startswith("; printing object "):
            object_id = line.split("printing object")[1].strip()
            if object_id not in known_objects:
                known_objects[object_id] = KnownObject(_clean_id(object_id), HullTracker.create())
            current_hull = known_objects[object_id].hull

        if line.startswith("; stop printing object "):
            current_hull = None

        if current_hull and line.strip().lower().startswith("g"):
            command, params = parse_gcode(line)
            if float(params.get("E", -1)) > 0 and "X" in params and "Y" in params:
                x = float(params["X"])
                y = float(params["Y"])
                current_hull.add_point(Point(x, y))


    infile.seek(0)
    for line in infile:
        if line.strip() and not line.startswith(";"):
            # Inject custom marker
            yield from header(len(known_objects))
            for object_id, hull in known_objects.values():
                yield from define_object(
                    object_id,
                    center=hull.center(),
                    polygon=hull.exterior(),
                )
            yield line
            break
        yield line

    for line in infile:
        yield line

        if line.startswith("; printing object "):
            yield from object_start_marker(known_objects[line.split("printing object")[1].strip()].name)

        if line.startswith("; stop printing object "):
            yield from object_end_marker(known_objects[line.split("printing object")[1].strip()].name)


def preprocess_ideamaker(infile):
    # This one is funnier
    # theres blocks like this, we can grab all these to get the names and ideamaker's IDs for them.
    #   ;PRINTING: test_bed_part0.3mf
    #   ;PRINTING_ID: 0

    known_objects: Dict[str, KnownObject] = {}
    current_hull: HullTracker = None

    for line in infile:
        if line.startswith(";TOTAL_NUM:"):
            total_num = int(line.split(":")[1].strip())
        if line.startswith(";PRINTING:"):
            name = line.split(":")[1].strip()
            id_line = next(infile)
            assert id_line.startswith(";PRINTING_ID:")
            id = id_line.split(":")[1].strip()
            # Ignore the internal non-object meshes
            if id == "-1":
                continue
            if id not in known_objects:
                known_objects[id] = KnownObject(_clean_id(name), HullTracker.create())
            current_hull = known_objects[id].hull

        if current_hull and line.strip().lower().startswith("g"):
            command, params = parse_gcode(line)
            if float(params.get("E", -1)) > 0 and "X" in params and "Y" in params:
                x = float(params["X"])
                y = float(params["Y"])
                current_hull.add_point(Point(x, y))

    infile.seek(0)

    current_object: Optional[KnownObject] = None
    for line in infile:
        yield line

        if line.strip() and not line.startswith(";"):
           break

    assert total_num == len(known_objects)
    yield from header(total_num)
    for id, (name, hull) in known_objects.items():
        yield from define_object(
            name,
            center=hull.center(),
            polygon=hull.exterior(),
        )
    yield "\n\n"

    for line in infile:
        yield line
        if line.startswith(";PRINTING_ID:"):
            printing_id = line.split(":")[1].strip()
            if current_object:
                yield from object_end_marker(current_object.name)
                current_object = None
            if printing_id == "-1":
                continue
            current_object = known_objects[printing_id]
            yield from object_start_marker(current_object.name)

        if line == ";REMAINING_TIME: 0\n" and current_object:
            yield from object_end_marker(current_object.name)
            current_object = None

    if current_object:
        yield from object_end_marker(current_object.name)


# Note:
#   Slic3r:     does not output any markers into GCode
#   Kisslicer:  does not output any markers into GCode
#   Kiri:Moto:  does not output any markers into GCode
#   Simplify3D: I was unable to figure out multiple processes
SLICERS: dict[str, Tuple[str, callable]] = {
    "superslicer": ("; generated by SuperSlicer", preprocess_slicer),
    "prusaslicer": ("; generated by PrusaSlicer", preprocess_slicer),
    "slic3r": ("; generated by Slic3r", preprocess_slicer),
    "cura": (";Generated with Cura_SteamEngine", preprocess_cura),
    "ideamaker": (";Sliced by ideaMaker", preprocess_ideamaker),
}


def identify_slicer_marker(line):
    for name, (marker, processor) in SLICERS.items():
        if line.strip().startswith(marker):
            logger.debug("Identified slicer %s", name)
            return processor


def preprocessor(infile, outfile):
    logger.debug("Identifying slicer")
    found_m486 = False
    processor = None
    for line in infile:
        if line.startswith("EXCLUDE_OBJECT_DEFINE") or line.startswith("DEFINE_OBJECT"):
            logger.info("GCode already supports cancellation")
            infile.seek(0)
            outfile.write(infile.read())
            return True

        if line.startswith("M486"):
            if not found_m486:
                logger.info("File has existing M486 markers, converting")
            found_m486 = True
            processor = preprocess_m486

        if not processor:
            processor = identify_slicer_marker(line)

    infile.seek(0)
    for line in processor(infile):
        outfile.write(line)

    return True


def process_file_for_cancellation(filename: PathLike, output_suffix=None) -> int:
    filepath = pathlib.Path(filename)
    outfilepath = filepath

    if output_suffix:
        outfilepath = outfilepath.with_name(outfilepath.stem + output_suffix + outfilepath.suffix)

    tempfilepath = pathlib.Path(tempfile.mktemp())

    with filepath.open("r") as fin:
        with tempfilepath.open("w") as fout:
            res = preprocessor(fin, fout)

    if res:
        if outfilepath.exists():
            outfilepath.unlink()
        shutil.move(tempfilepath, outfilepath)

    else:
        tempfilepath.unlink()

    return res


def _main():
    argparser = argparse.ArgumentParser()
    argparser.add_argument(
        "--output-suffix",
        "-o",
        help="Add a suffix to gcoode output. Without this, gcode will be rewritten in place",
    )
    argparser.add_argument(
        "--disable-shapely", help="Disable using shapely to generate a hull polygon for objects", action="store_true"
    )
    argparser.add_argument("gcode", nargs="*")

    exitcode = 0

    args = argparser.parse_args()
    if args.disable_shapely:
        global shapely
        shapely = None

    for filename in args.gcode:
        if not process_file_for_cancellation(filename, args.output_suffix):
            exitcode = 1

    sys.exit(exitcode)


if __name__ == "__main__":
    _main()

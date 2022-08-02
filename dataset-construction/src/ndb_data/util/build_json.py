#
# Copyright (c) 2021 Facebook, Inc. and its affiliates.
#
# This file is part of NeuralDB.
# See https://github.com/facebookresearch/NeuralDB for further info.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import glob
import csv
import json
from argparse import ArgumentParser
from collections import defaultdict

import re


def read_csv(f):
    next(f)
    reader = csv.DictReader(f)

    templates = defaultdict(set)

    for template in reader:

        if len(template["fact"]):
            templates["fact"].add(template["fact"])

        if len(template["bool"]) and template["bool_answer"].lower() in [
            "true",
            "t",
            "1",
            "yes",
            "y",
        ]:
            templates["bool"].add((template["bool"], template["bool_answer"]))

        if len(template["set"]):
            templates["set"].add((template["set"], template["set_projection"]))

        if len(template["count"]):
            templates["count"].add((template["count"], template["count_projection"]))

        if len(template["min"]):
            templates["min"].add((template["min"], template["min_projection"]))

        if len(template["max"]):
            templates["max"].add((template["max"], template["max_projection"]))

        if len(template["argmin"]):
            templates["argmin"].add((template["argmin"], template["argmin_projection"]))

        if len(template["argmax"]):
            templates["argmax"].add((template["argmax"], template["argmax_projection"]))

        templates["_subject"] = "$s"
        templates["_object"] = "$o"

    return {k: list(v) if isinstance(v, set) else v for k, v in templates.items()}


def swap_so(statement):
    return statement.replace("$s", "$tmp_s").replace("$o", "$s").replace("$tmp_s", "$o")


def make_symmetric(k, templates):

    if k.startswith("_"):
        return templates
    out = []
    out.extend(templates)
    out.extend([(swap_so(t[0]), swap_so(t[1])) for t in templates if len(t) == 2])
    out.extend([swap_so(t) for t in templates if isinstance(t, str)])
    return out


if __name__ == "__main__":
    print("Generate")
    parser = ArgumentParser()
    parser.add_argument("version")
    args = parser.parse_args()
    # Read all CSV files in dir
    files = glob.glob(f"configs/for_{args.version}/*.csv")
    print(files)

    all_templates = {}
    for file in files:
        match = re.match(r".*(P[0-9]+).*", file)

        if match is not None:
            name = match[1]

            with open(file) as f:
                template = read_csv(f)

            if name in {"P47", "P26"}:
                all_templates[name] = {
                    prop: make_symmetric(prop, rules)
                    for prop, rules in template.items()
                }
            else:
                all_templates[name] = template

    with open(f"configs/generate_{args.version}.json", "w+") as of:
        json.dump(all_templates, of, indent=4)

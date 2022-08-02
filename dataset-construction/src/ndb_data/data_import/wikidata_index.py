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
import bz2
import json
from collections import defaultdict
from json import JSONDecodeError

import pydash
from argparse import ArgumentParser

from tqdm import tqdm

from ndb_data.wikidata_common.wikidata import Wikidata


def read_dump(wikidata_file):
    with bz2.open(wikidata_file, mode="rt") as f:
        f.read(2)
        for line in f:
            yield line.rstrip(",\n")


def get_indexable(instance):
    wikidata_id = pydash.get(instance, "id")
    english_name = pydash.get(instance, "labels.en.value")

    claims = pydash.get(instance, "claims")

    properties = set()
    property_entity = defaultdict(list)
    for property, claims in claims.items():
        properties.add(property)
        for claim in claims:
            property_entity[property].append(
                (
                    pydash.get(claim, "mainsnak.datavalue.value"),
                    list(pydash.get(claim, "qualifiers").values())
                    if pydash.get(claim, "qualifiers") is not None
                    else None,
                )
            )
    sitelinks = pydash.get(instance, "sitelinks")
    enwiki = pydash.get(instance, "sitelinks.enwiki.title")
    yield wikidata_id, english_name, sitelinks, enwiki, list(properties), dict(
        property_entity
    )


def index_dump(dump):
    for line in dump:
        try:
            yield from get_indexable(json.loads(line))
        except JSONDecodeError as e:
            print(e)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("wikidata_file")
    args = parser.parse_args()

    wiki = Wikidata()
    collection = wiki.collection

    insert_count = 0
    dump = read_dump(args.wikidata_file)
    batch = []

    _tqdm_iter = tqdm(index_dump(dump), total=90e6)
    for w_id, e_name, sitelinks, enwiki, props, prop_dict in _tqdm_iter:
        batch.append(
            {
                "wikidata_id": w_id,
                "english_name": e_name,
                "english_wiki": enwiki,
                "property_types": props,
                "properties": prop_dict,
                "sitelinks": list(sitelinks.values()),
            }
        )

        if len(batch) >= 5000:
            collection.insert_many(batch)
            batch = []
            insert_count += 1

            _tqdm_iter.desc = f"Insert batch {insert_count}"

    print("last")
    collection.insert_many(batch)

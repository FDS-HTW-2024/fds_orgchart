import argparse
from concurrent.futures import Executor, ThreadPoolExecutor
import json
import os
from queue import SimpleQueue, Queue
import sys
from typing import Iterator, Optional

from organigram_extract import Document, Drawing, TextPipeline
import organigram_extract.pdf as pdf

def run():
    parser = argparse.ArgumentParser(prog='Organigramm Extract')

    parser.add_argument('input_path', help='source file for extraction')
    parser.add_argument('-o', '--output_path', help='output file to write the extracted content')
    parser.add_argument('-m', '--model', help='llm to use for content extraction')
    parser.add_argument('-k', '--key', help='specify API Key (overwrites previously specified key)')
    parser.add_argument('-s', '--schema_file', help='path to json schema to use for parsing. Overrides default json schema',
                       default='src/organigram_extract/default_schema.json')

    args = parser.parse_args()
    config = {key:value for (key, value) in vars(args).items() if value != None}

    if args.key == None and "API_KEY" in os.environ:
        config["key"] = os.environ["API_KEY"]

    worker_threads = 4

    with ThreadPoolExecutor(max_workers=worker_threads) as executor:
        task_queue = Queue(1)

        # Process all text in a separate thread
        #
        # The text pipeline components are created once to avoid using too
        # much memory accidentally.
        text_processing = executor.submit(process_text, task_queue, config)

        process_file(executor, task_queue, args.input_path, args.output_path)

        # Shutdown text processing thread
        task_queue.put(None)
        text_processing.result()

def process_file(executor: Executor, task_queue: Queue, input: str, output: Optional[str]):
    drawings = pdf.open(input)
    results = executor.map(lambda d: process_drawing(d, task_queue), drawings)
    content = {index:result for (index, result) in enumerate(results)}

    if output != None:
        with open(output, "w", encoding="utf-8") as file:
            json.dump(content, file, ensure_ascii=False, separators=(",", ":"))
    else:
        json.dump(content, sys.stdout, ensure_ascii=False, indent=4)

def process_drawing(drawing: Drawing, task_queue: Queue):
    document = Document.extract(drawing)

    if len(document.text_blocks) == 0:
        return []

    inputs = tuple(document.text_contents.values())
    oneshot = SimpleQueue()

    task_queue.put((oneshot, inputs))

    outputs = oneshot.get()
    content = [output for output in outputs if output["type"] != None or 0 < len(output["persons"])]

    return {"content": content}

def process_text(task_queue: Queue, config):
    with TextPipeline(config) as pipeline:
        for (oneshot, inputs) in iter(task_queue.get, None):
            outputs = tuple(pipeline.process(inputs))

            oneshot.put(outputs)

# TODO: Deal with directories
# async def parse(input_path: str, output_file: str, model_name: str, schema_path: str):
#     model: Model = llm.get_model(model_name)
#     model.key = os.environ['API_KEY']
#     schema = load_json(schema_path)

#     if ntpath.isfile(input_path):
#         await extract_from_file(input_path, output_file, model, schema)
#     elif ntpath.isdir(input_path):
#         print("parse orgcharts from directory")
#         for file in os.listdir(input_path):
#             head, _ = file.split(".")
#             out_name, ending = output_file.split(".")
#             out_file = f"{out_name}_{head}.{ending}"
#             await extract_from_file(file, out_file, model, schema)
#     else:
#         print("file path does not exists", file=sys.stderr)

# async def extract_from_file(file_path: str, output_path: str, model, schema):
#     import ntpath
#     page = pymupdf.open(file_path)[0]
#     (_, _, _, _, content_nodes) = extract(page)


#     start = timeit.default_timer()
#     extract_results = await extract_from_content(model, content_nodes, str(schema), max_concurrency=5)

#     head, tail = ntpath.split(file_path)
#     file_name = tail or ntpath.basename(head)
#     output_json = {
#         "fileName": file_name,
#         "content" : extract_results
#     }

#     end = timeit.default_timer()
#     print("took", end - start)

#     if output_path:
#         with open(output_path, 'w+', encoding='utf-8') as out:
#             json.dump(output_json, out, ensure_ascii=False)
#     else:
#         print(json.dumps(output_json, ensure_ascii=False, indent=2))
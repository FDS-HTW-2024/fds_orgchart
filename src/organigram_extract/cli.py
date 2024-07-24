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
    parser = argparse.ArgumentParser(prog="Organigramm Extract")

    parser.add_argument("input_path",
                        help="source file or directory containing source files for extraction")
    parser.add_argument("-o", "--output_path",
                        help="output file or directory to write the extracted content to")
    parser.add_argument("-m", "--model",
                        help="LLM to use for content extraction")
    parser.add_argument("-k", "--key",
                        help="specify API key for LLM")
    parser.add_argument("-d", "--data_path",
                        help="path containing files to override data files (e.g. schema.json)")
    parser.add_argument("-w", "--worker_threads",
                        help="max amount of spawned threads for page extraction and LLM tasks",
                        type=int,
                        default=4)

    args = parser.parse_args()
    config = {key:value for (key, value) in vars(args).items() if value != None}

    if args.key == None and "API_KEY" in os.environ:
        config["key"] = os.environ["API_KEY"]

    with ThreadPoolExecutor(max_workers=args.worker_threads) as executor:
        task_queue = Queue(1)

        # Process all text in a separate thread
        #
        # The text pipeline components are created once to avoid using too
        # much memory accidentally.
        text_processing = executor.submit(process_text, task_queue, config)

        input_path = args.input_path
        output_path = args.output_path

        if os.path.isfile(input_path):
            process_file(executor, task_queue, input_path, output_path)
        elif os.path.isdir(args.input_path):
            for filename in os.listdir(args.input_path):
                input_file = os.path.join(input_path, filename)
                output_file = output_path

                if output_path != None:
                    (name, _) = os.path.splitext(filename)
                    output_file = os.path.join(output_path, name + ".json")
                   
                process_file(executor, task_queue, input_file, output_file)
        else:
            raise FileNotFoundError()

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
    with TextPipeline(data_path=config.get("data_path"),
                      llm_model=config.get("model"),
                      llm_key=config.get("key")) as pipeline:
        for (oneshot, inputs) in iter(task_queue.get, None):
            outputs = tuple(pipeline.process(inputs))

            oneshot.put(outputs)

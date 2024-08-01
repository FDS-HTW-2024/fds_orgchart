import argparse
from concurrent.futures import Executor, ThreadPoolExecutor
import errno
import json
import logging
import os
from queue import SimpleQueue, Queue
import sys
from typing import Iterator, Optional

from orgxtract import Document, Drawing, TextPipeline
import orgxtract.pdf as pdf

def run():
    parser = argparse.ArgumentParser(prog=__package__)

    parser.add_argument("input",
                        help="source file or directory containing source files for extraction")
    parser.add_argument("-o", "--output",
                        help="target file or directory to write the extracted content to")
    parser.add_argument("-m", "--model",
                        help="name of LLM to use for content extraction")
    parser.add_argument("-k", "--key",
                        help="API key of LLM")
    parser.add_argument("-d", "--data-path",
                        help="path containing files to override data files (e.g. schema.json)")
    parser.add_argument("-w", "--worker-threads",
                        help="max amount of spawned threads for page extraction and LLM tasks",
                        type=int,
                        default=4)
    parser.add_argument("--log-level",
                        help="logging level",
                        choices=["NOTSET", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                        default="INFO")

    args = parser.parse_args()
    config = {key:value for (key, value) in vars(args).items() if value != None}

    if args.key == None and "API_KEY" in os.environ:
        config["key"] = os.environ["API_KEY"]

    logging.basicConfig(level=args.log_level)

    executor = ThreadPoolExecutor(max_workers=args.worker_threads)
    task_queue = Queue(1)

    try:
        # Process all text in a separate thread
        #
        # The text pipeline components are created once to avoid using too
        # much memory accidentally.
        text_processing = executor.submit(process_text, task_queue, config)

        input = args.input
        output = args.output

        if os.path.isfile(input):
            process_file(executor, task_queue, input, output)
        elif os.path.isdir(input):
            for filename in os.listdir(input):
                input_file = os.path.join(input, filename)
                output_file = output

                if output != None:
                    (name, _) = os.path.splitext(filename)
                    output_file = os.path.join(output, name + ".json")
                   
                process_file(executor, task_queue, input_file, output_file)
        else:
            raise FileNotFoundError(errno.ENOENT,
                                    os.strerror(errno.ENOENT),
                                    input)
    finally:
        executor.shutdown(wait=False, cancel_futures=True)
        # Signals text processing thread to shutdown
        task_queue.put(None)

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
    result = {}
    metadata = {}
    content = []

    for output in outputs:
        if "date" in output:
            metadata["date"] = output["date"]
            del output["date"]

        if (output.get("name") != None or bool(output.get("persons"))):
            content.append(output)
            

    if 0 < len(metadata):
        result["metadata"] = metadata

    result["content"] = content

    return result

def process_text(task_queue: Queue, config):
    with TextPipeline(data_path=config.get("data_path"),
                      llm_model=config.get("model"),
                      llm_key=config.get("key"),
                      n_threads=config.get("worker_threads")) as pipeline:
        for (oneshot, inputs) in iter(task_queue.get, None):
            outputs = tuple(pipeline.pipe(inputs))

            oneshot.put(outputs)

    # Shutdowns any waiting producer threads (process_drawing)
    while 0 < task_queue.qsize():
        (oneshot, _) = task_queue.get_nowait()

        oneshot.put(())

def print_progress_bar(iteration, total, prefix = '', suffix = '', decimals = 1, length = 100, fill = '█', printEnd = "\r"):
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end = printEnd)
    if iteration == total: 
        print()

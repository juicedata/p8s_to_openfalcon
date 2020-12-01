#!/usr/bin/env python
from __future__ import print_function
import re
import sys
import time
import json
import argparse
import logging
try:
    from urllib.request import urlopen, Request
except ImportError:
    from urllib2 import urlopen, Request


logger = logging.Logger(__file__)
handler = logging.StreamHandler()
handler.setFormatter(
    logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)


def new_falcon_item(endpoint, metric, timestamp, step, value, counter_type, tags):
    return {
        "endpoint": endpoint,
        "metric": metric,
        "timestamp": timestamp,
        "step": step,
        "value": value,
        "counterType": counter_type,
        "tags": ",".join("%s=%s" % (k, v) for k, v in tags.items()),
    }


def _parse_labels(it, text):
    METRIC_LABEL_NAME_RE = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')

    # The { has already been parsed.
    state = 'startoflabelname'
    labelname = []
    labelvalue = []
    labels = {}

    for char in it:
        if state == 'startoflabelname':
            if char == '}':
                state = 'endoflabels'
            else:
                state = 'labelname'
                labelname.append(char)
        elif state == 'labelname':
            if char == '=':
                state = 'labelvaluequote'
            else:
                labelname.append(char)
        elif state == 'labelvaluequote':
            if char == '"':
                state = 'labelvalue'
            else:
                raise ValueError("Invalid line: " + text)
        elif state == 'labelvalue':
            if char == '\\':
                state = 'labelvalueslash'
            elif char == '"':
                if not METRIC_LABEL_NAME_RE.match(''.join(labelname)):
                    raise ValueError("Invalid line: " + text)
                labels[''.join(labelname)] = ''.join(labelvalue)
                labelname = []
                labelvalue = []
                state = 'endoflabelvalue'
            else:
                labelvalue.append(char)
        elif state == 'endoflabelvalue':
            if char == ',':
                state = 'labelname'
            elif char == '}':
                state = 'endoflabels'
            else:
                raise ValueError("Invalid line: " + text)
        elif state == 'labelvalueslash':
            state = 'labelvalue'
            if char == '\\':
                labelvalue.append('\\')
            elif char == 'n':
                labelvalue.append('\n')
            elif char == '"':
                labelvalue.append('"')
            else:
                labelvalue.append('\\' + char)
        elif state == 'endoflabels':
            if char == ' ':
                break
            else:
                raise ValueError("Invalid line: " + text)
    return labels


def to_falcon_item(type_, line, step, timestamp, endpoint):
    info, val = line.rsplit(" ", 1)
    metric, _, labels = info.partition('{')
    parsed_labels = _parse_labels(labels, line)
    return new_falcon_item(endpoint, metric, timestamp, step, val, type_, parsed_labels)

TYPE_PREFIX = "# TYPE "


def parse_falcon_samples(lines, step, endpoint='test'):
    ts = int(time.time())
    cur_type = None
    while True:
        line = next(lines, None)
        if line is None:
            break
        if line[0] != '#':
            if cur_type not in ('COUNTER', 'GAUGE'):
                logger.warning(
                    "Ignoring sample of unsupported type(%r): %r",
                    cur_type, line
                )
                continue
            yield to_falcon_item(cur_type, line, step, ts, endpoint)
        elif line.startswith(TYPE_PREFIX):
            parts = line[len(TYPE_PREFIX):].split(" ")
            cur_type = parts[1].upper()


def push_to_openfalcon(url, samples):
    payload = json.dumps(list(samples)).encode('utf8')
    request = Request(
        url, payload,
        {'Content-Type': 'application/json', 'Content-Length': len(payload)}
    )
    logger.debug("Pushing samples to %s", url)
    response = urlopen(request, timeout=3)
    response.read()
    response.close()
    logger.debug("Pushed samples to %s", url)


def read_metric_source(url):
    logger.debug("Start reading metrics from %s", url)
    if url.startswith('http'):
        request = Request(url)
        request.add_header('Accept-encoding', 'gzip')
        request.add_header('User-Agent', 'JuiceFS')
        response = urlopen(request, timeout=5)
        return (l.decode('utf8').rstrip() for l in response.readlines())
    elif url == '-': # read from stdin
        return (l.decode('utf8').rstrip() for l in sys.stdin.readlines())
    else:
        raise ValueError('Unsupported url format')


def sync(source_url, falcon_push_api, endpoint, step, output_only):
    try:
        lines = read_metric_source(source_url)
        samples = parse_falcon_samples(lines, step, endpoint)

        if output_only:
            for s in samples:
                print(s)
            print()
        else:
            push_to_openfalcon(falcon_push_api, samples)
    except Exception:
        logger.exception("Error occured")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "source_url",
        help="URL of the metrics source API",
    )
    parser.add_argument(
        "step",
        help="The reporting interval in seconds",
        type=int,
    )
    parser.add_argument(
        "--falcon_push_api",
        help="URL of the open-falcon push API"
    )
    parser.add_argument(
        "--endpoint",
        help="Endpoint of the open-falcon samples",
        default="test"
    )
    parser.add_argument(
        "--output_only",
        help="Output the transformed sample without actually pushing",
        action="store_true"
    )
    parser.add_argument(
        "--loop",
        help="Sync periodically in a loop",
        action="store_true"
    )
    args = parser.parse_args()

    if not args.output_only and not args.falcon_push_api:
        parser.print_usage()
        print("falcon_push_api not provided")
        sys.exit(1)

    if args.loop:
        while True:
            sync(args.source_url, args.falcon_push_api,  args.endpoint, args.step, args.output_only)
            time.sleep(args.step)
    else:
        sync(args.source_url, args.falcon_push_api, args.endpoint, args.step, args.output_only)


if __name__ == "__main__":
    main()

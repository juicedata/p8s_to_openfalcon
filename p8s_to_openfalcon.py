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
logger.addHandler(logging.StreamHandler())


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


def to_falcon_item(type_, line, step, timestamp):
    info, val = line.rsplit(" ", 1)
    metric, _, labels = info.partition('{')
    parsed_labels = _parse_labels(labels, line)
    return new_falcon_item('test', metric, timestamp, step, val, type_, parsed_labels)

TYPE_PREFIX = "# TYPE "


def parse_falcon_samples(lines, step):
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
            yield to_falcon_item(cur_type, line, step, ts)
        elif line.startswith(TYPE_PREFIX):
            parts = line[len(TYPE_PREFIX):].split(" ")
            cur_type = parts[1].upper()


def push_to_openfalcon(url, samples):
    payload = json.dumps(list(samples))
    request = Request(
        url, payload,
        {'Content-Type': 'application/json', 'Content-Length': len(payload)}
    )
    response = urlopen(request)
    response.read()
    response.close()


def read_metric_source(url):
    request = Request(url)
    request.add_header('Accept-encoding', 'gzip')
    request.add_header('User-Agent', 'JuiceFS')
    response = urlopen(request, timeout=5)
    return (l.rstrip() for l in response.readlines())


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
        help="Endpoint of the open-falcon samples"
    )
    parser.add_argument(
        "--output_only",
        help="Output the transformed sample without actually pushing",
        action="store_true"
    )
    args = parser.parse_args()

    lines = read_metric_source(args.source_url)
    samples = parse_falcon_samples(lines, args.step)

    if args.output_only:
        for s in samples:
            print(s)
        return
    
    if not args.endpoint:
        parser.print_usage()
        print("Endpoint not provided")
        sys.exit(1)

    push_to_openfalcon(args.endpoint, samples)


if __name__ == "__main__":
    main()
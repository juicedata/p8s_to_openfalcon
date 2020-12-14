# p8s_to_openfalcon

## Installation

```bash
curl -L https://raw.githubusercontent.com/juicedata/p8s_to_openfalcon/master/p8s_to_openfalcon.py
chmod +x p8s_to_openfalcon.py
```

## Usage
```bash
usage: ./p8s_to_openfalcon.py [-h] [--falcon_push_api FALCON_PUSH_API]
                            [--endpoint ENDPOINT] [--output_only] [--loop]
                            source_url step
```
_FALCON_PUSH_API_: The push api for metrics, required when `--output_only` is not specified
_ENDPOINT_: `endpoint` field in [open-falcon metric](https://book.open-falcon.org/zh_0_2/usage/data-push.html#api%E8%AF%A6%E8%A7%A3), such as `$HOSTNAME`, default is `test`
_--output_only_: Output the transformed metrics to _stdout_ instand of pushing to open-falcon
_--loop_: Support periodically sync metrics when the _source_url_ is a http[s] endpoint
_source_url_: Required. P8S metric endpoint. When `-` is provided, metrics are fetched from _stdin_
_step_: Required. `step` field in open-falcon metric

### Check the parsed samples without actually pushing to an open-falcon API
  ```bash
./p8s_to_openfalcon.py https://juicefs.com/console/vol/<filesystem>/metrics?token=<token> 10 --output_only
  ```

### Sync the metrics from command's stdout
```bash
./collect_command | ./p8s_to_openfalcon.py - 30 --endpoint=$HOSTNAME --falcon_push_api <your_openfalcon_host>/v1/push
```

### Sync the metrics periodically to an open-falcon API
  ```bash
./p8s_to_openfalcon.py https://juicefs.com/console/vol/<filesystem>/metrics?token=<token> 10 --falcon_push_api <your_openfalcon_host>/v1/push --loop
```

### Sync only once
  ```bash
./p8s_to_openfalcon.py https://juicefs.com/console/vol/<filesystem>/metrics?token=<token> 10 --falcon_push_api <your_openfalcon_host>/v1/push
```

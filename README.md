# p8s_to_openfalcon

## Installation

```bash
curl -L https://raw.githubusercontent.com/juicedata/p8s_to_openfalcon/master/p8s_to_openfalcon.py
chmod +x p8s_to_openfalcon.py
```

## Usage

### Check the parsed samples without actually pushing to an open-falcon API
  ```bash
./p8s_to_openfalcon.py https://juicefs.com/console/vol/<filesystem>/metrics?token=<token> 10 --output_only
  ```
### Sync the metrics periodically to an open-falcon API
  ```bash
./p8s_to_openfalcon.py https://juicefs.com/console/vol/<filesystem>/metrics?token=<token> 10 --endpoint <your_openfalcon_host>/v1/push
```

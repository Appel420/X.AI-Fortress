main.py
from logging_utils import setup_logging
from config_loader import load_config
from audio_processor import load_sample, listen
from cli import parse_args
from exceptions import ConfigError, AudioError

DEFAULTS = {
    "threshold": 3000,
    "chunk": 1024,
    "arawav": "arasample.wav",
    "log_level": "INFO"
}

def main():
    args = parse_args()

    logger = setup_logging(DEFAULTS["log_level"])

    logger.info(f"Starting Ara Wake Word Detector. Config file: {args.config}")

    try:
        config = load_config(args.config, DEFAULTS)
    except ConfigError as e:
        logger.error(e)
        logger.warning("Falling back to default configuration.")
        config = DEFAULTS

    logger = setup_logging(config.get("log_level", "INFO"))

    logger.info(f"Using configuration file: {args.config}")
    logger.info("Loaded configuration parameters:")
    for key, value in config.items():
        logger.info(f"  {key}: {value}")

    try:
        sample = load_sample(config["arawav"])
        logger.debug(f"Wake word sample loaded: {config['arawav']} with {len(sample)} samples")
    except AudioError as e:
        logger.error(e)
        return

    try:
        listen(config, sample, logger)
    except AudioError as e:
        logger.error(e)

if __name__ == "__main__":
    main()

"""Mapeo curado ticker -> id de CoinGecko. Los simbolos son ambiguos (decenas
de monedas comparten ticker), por eso no se usa /search: un ticker fuera de
esta lista no tiene cotizacion automatica y se carga a mano."""

from typing import NamedTuple, Optional


class CryptoAsset(NamedTuple):
    ticker: str
    coingecko_id: str
    name: str


_ASSETS = [
    CryptoAsset("BTC", "bitcoin", "Bitcoin"),
    CryptoAsset("ETH", "ethereum", "Ethereum"),
    CryptoAsset("USDT", "tether", "Tether"),
    CryptoAsset("USDC", "usd-coin", "USD Coin"),
    CryptoAsset("DAI", "dai", "Dai"),
    CryptoAsset("SOL", "solana", "Solana"),
    CryptoAsset("BNB", "binancecoin", "BNB"),
    CryptoAsset("XRP", "ripple", "XRP"),
    CryptoAsset("ADA", "cardano", "Cardano"),
    CryptoAsset("DOGE", "dogecoin", "Dogecoin"),
    CryptoAsset("TRX", "tron", "TRON"),
    CryptoAsset("TON", "the-open-network", "Toncoin"),
    CryptoAsset("DOT", "polkadot", "Polkadot"),
    CryptoAsset("POL", "polygon-ecosystem-token", "POL (ex MATIC)"),
    CryptoAsset("LTC", "litecoin", "Litecoin"),
    CryptoAsset("AVAX", "avalanche-2", "Avalanche"),
    CryptoAsset("LINK", "chainlink", "Chainlink"),
    CryptoAsset("XLM", "stellar", "Stellar"),
    CryptoAsset("BCH", "bitcoin-cash", "Bitcoin Cash"),
    CryptoAsset("ATOM", "cosmos", "Cosmos"),
    CryptoAsset("UNI", "uniswap", "Uniswap"),
    CryptoAsset("SHIB", "shiba-inu", "Shiba Inu"),
]

CRYPTO_ASSETS: dict[str, CryptoAsset] = {a.ticker: a for a in _ASSETS}


def get_asset(ticker: Optional[str]) -> Optional[CryptoAsset]:
    return CRYPTO_ASSETS.get(ticker.strip().upper()) if ticker else None


def list_assets() -> list[CryptoAsset]:
    return list(_ASSETS)

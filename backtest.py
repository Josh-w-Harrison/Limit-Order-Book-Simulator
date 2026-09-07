import itertools
from functools import partial

def run_backtest(simulator, n_ticks=None):
    if simulator.strategy is None:
        raise ValueError("Simulator has no strategy attached; cannot run backtest.")

    if n_ticks is None:
        history = simulator.run_replay()
    else:
        history = simulator.run(n_ticks)

    final_inventory = simulator.strategy.inventory
    final_reference_price = simulator.strategy.reference_price
    realized_pnl = simulator.strategy.cash
    unrealized_pnl = final_inventory * final_reference_price if final_reference_price is not None else 0
    total_pnl = realized_pnl + unrealized_pnl
    trade_count = sum(len(entry['fills']) for entry in history)

    report = {
        'final_inventory': final_inventory,
        'final_reference_price': final_reference_price,
        'realized_pnl': realized_pnl,
        'unrealized_pnl': unrealized_pnl,
        'total_pnl': total_pnl,
        'trade_count': trade_count,
        'history': history,
        'pnl_history': build_pnl_history(simulator.strategy),
    }

    return report


def build_pnl_history(strategy):
    pnl_history = []
    for snapshot in strategy.history:
        realized = snapshot['cash']
        unrealized = (
            snapshot['inventory'] * snapshot['reference_price']
            if snapshot['reference_price'] is not None else 0
        )
        pnl_history.append({
            'inventory': snapshot['inventory'],
            'realized_pnl': realized,
            'unrealized_pnl': unrealized,
            'total_pnl': realized + unrealized,
        })
    return pnl_history


def optimise_parameters(param_grid, make_train_simulator, make_test_simulator):
    keys = list(param_grid.keys())
    all_results = []

    for combo in itertools.product(*param_grid.values()):
        params = dict(zip(keys, combo))
        train_sim, train_n_ticks = make_train_simulator(params)
        train_report = run_backtest(train_sim, n_ticks=train_n_ticks)
        all_results.append({'params': params, 'train_pnl': train_report['total_pnl']})

    best_result = max(all_results, key=lambda result: result['train_pnl'])
    best_params = best_result['params']

    test_sim, test_n_ticks = make_test_simulator(best_params)
    test_report = run_backtest(test_sim, n_ticks=test_n_ticks)

    return {
        'best_params': best_params,
        'train_pnl': best_result['train_pnl'],
        'test_pnl': test_report['total_pnl'],
        'all_results': all_results,
    }


LOBSTER_MESSAGE_CSV = "data/LOBSTER_SampleFile_AMZN_2012-06-21_10/AMZN_2012-06-21_34200000_57600000_message_10.csv"


def _lobster_row_count(message_csv_path):
    with open(message_csv_path) as f:
        return sum(1 for _ in f)


def make_lobster_train_simulator(params, strategy_cls=None, message_csv_path=LOBSTER_MESSAGE_CSV, train_fraction=0.7):
    from market_data import LOBSTERMarketDataGenerator
    from order_book import OrderBook
    from simulator import Simulator
    from market_maker import MarketMaker

    if strategy_cls is None:
        strategy_cls = MarketMaker

    n_rows = _lobster_row_count(message_csv_path)
    split_row = int(n_rows * train_fraction)
    generator = LOBSTERMarketDataGenerator(message_csv_path, end_row=split_row)
    order_book = OrderBook()
    strategy = strategy_cls(**params)
    simulator = Simulator(order_book, generator, strategy=strategy)
    return simulator, None


def make_lobster_test_simulator(params, strategy_cls=None, message_csv_path=LOBSTER_MESSAGE_CSV, train_fraction=0.7):
    from market_data import LOBSTERMarketDataGenerator
    from order_book import OrderBook
    from simulator import Simulator
    from market_maker import MarketMaker

    if strategy_cls is None:
        strategy_cls = MarketMaker

    n_rows = _lobster_row_count(message_csv_path)
    split_row = int(n_rows * train_fraction)
    generator = LOBSTERMarketDataGenerator(message_csv_path, start_row=split_row)
    order_book = OrderBook()
    strategy = strategy_cls(**params)
    simulator = Simulator(order_book, generator, strategy=strategy)
    return simulator, None


if __name__ == "__main__":
    from market_data import MarketDataGenerator
    from order_book import OrderBook
    from simulator import Simulator
    from market_maker import MarketMaker

    generator = MarketDataGenerator(initial_price=100.0, seed=42)
    order_book = OrderBook()
    strategy = MarketMaker(half_spread=0.5, skew_coefficient=0.01, quote_size=10)
    simulator = Simulator(order_book, generator, seed=42, strategy=strategy)

    report = run_backtest(simulator, n_ticks=400)

    print(f"Final inventory:      {report['final_inventory']}")
    print(f"Final reference price: {report['final_reference_price']:.4f}")
    print(f"Realized PnL:          {report['realized_pnl']:.2f}")
    print(f"Unrealized PnL:        {report['unrealized_pnl']:.2f}")
    print(f"Total PnL:             {report['total_pnl']:.2f}")
    print(f"Trade count:           {report['trade_count']}")
    print(f"Ticks recorded in pnl_history: {len(report['pnl_history'])}")

    pnl_history = report['pnl_history']
    sample_every = max(1, len(pnl_history) // 10)
    print("\nSampled PnL over time (every "
          f"{sample_every} ticks):")
    for i in range(0, len(pnl_history), sample_every):
        snap = pnl_history[i]
        print(f"  tick {i + 1:4d}: inventory={snap['inventory']:4d}  "
              f"realized={snap['realized_pnl']:9.2f}  "
              f"unrealized={snap['unrealized_pnl']:9.2f}  "
              f"total={snap['total_pnl']:9.2f}")

    # Grid search against real LOBSTER order flow.
    param_grid = {
        'half_spread': [0.02, 0.05, 0.1, 0.2],
        'skew_coefficient': [0.0005, 0.001, 0.005],
        'quote_size': [10],
    }

    print("\n--- Grid search against real LOBSTER data (train/test split) ---")
    result = optimise_parameters(param_grid, make_lobster_train_simulator, make_lobster_test_simulator)

    print(f"Best params: {result['best_params']}")
    print(f"Train PnL:   {result['train_pnl']:.2f}")
    print(f"Test PnL:    {result['test_pnl']:.2f}")
    print("\nAll combinations (sorted by train PnL):")
    for r in sorted(result['all_results'], key=lambda r: -r['train_pnl']):
        print(f"  {r['params']}  train_pnl={r['train_pnl']:.2f}")

    # Grid search the Avellaneda-Stoikov strategy against the same real LOBSTER order flow.
    from avellaneda_stoikov import AvellanedaStoikovMarketMaker

    avellaneda_param_grid = {
        # log-spaced -- gamma is not order-1 (see the scale note in avellaneda_stoikov.py);
        # a linear grid here would land entirely inside one degenerate regime. Narrowed to
        # two extremes after the first sweep showed gamma barely moves PnL at this scale --
        # k and max_inventory turned out to matter far more, so resolution went there instead.
        'gamma': [1e-6, 1e-4],
        'sigma': [0.01, 0.02],
        'k': [3, 5, 10, 20],  # first sweep only tried 10/20 and k=10 dominated -- pushing lower to see if the trend continues
        'terminal_time': [57600],  # the actual LOBSTER session close (seconds after midnight) -- a property of the data file, not a free parameter
        'quote_size': [10],
        'max_inventory': [25, 50, 100],  # first sweep fixed this at 50 by feel -- now actually searched
    }

    avellaneda_train_builder = partial(make_lobster_train_simulator, strategy_cls=AvellanedaStoikovMarketMaker)
    avellaneda_test_builder = partial(make_lobster_test_simulator, strategy_cls=AvellanedaStoikovMarketMaker)

    print("\n--- Avellaneda-Stoikov grid search against real LOBSTER data (train/test split) ---")
    avellaneda_result = optimise_parameters(avellaneda_param_grid, avellaneda_train_builder, avellaneda_test_builder)

    print(f"Best params: {avellaneda_result['best_params']}")
    print(f"Train PnL:   {avellaneda_result['train_pnl']:.2f}")
    print(f"Test PnL:    {avellaneda_result['test_pnl']:.2f}")
    print("\nAll combinations (sorted by train PnL):")
    for r in sorted(avellaneda_result['all_results'], key=lambda r: -r['train_pnl']):
        print(f"  {r['params']}  train_pnl={r['train_pnl']:.2f}")

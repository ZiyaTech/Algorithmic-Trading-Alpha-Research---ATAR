# Limitations

ATAR is research software. Source availability and computational sophistication do not establish a trading edge, investment readiness or live execution quality.

## Reference execution

The included engine uses one position per candidate, fixed entry notional, completed-bar decisions, next-open fills and constant per-side costs expressed relative to entry notional. Returns are additive fixed-notional returns, not reinvested portfolio returns. Drawdown is measured on that fixed-notional marked-to-market curve, not on a leveraged brokerage account.

An existing position that gaps through its stop or target fills at the open. Within a bar, a stop takes precedence when both stop and target are touched. There is no queue, liquidity, volume, market impact, financing, currency conversion, broker netting or trailing-stop simulation. The last close forces a stage-boundary exit. A decision from an earlier window cannot open the first position of a new window.

Trade records report the exit bar timestamp, not an inferred exact intrabar fill time. Artificial prices are not a faithful market or a profitability benchmark.

## Strategy adaptation

Core strategies operate on one supplied timeframe. The original minute-aligned VBT PinBar path and the IH quote callback are separately identified. Their indicators, event availability and initial state may differ from the core reference environment. Signal agreement is not trade or return equivalence.

## Evidence

The source-derived formulas, completed-bar adapters and reference engine are tested locally. Tests establish particular invariants, not universal absence of look-ahead or financial bugs. Optional VBT Pro runtime tests require that separately installed dependency. A skipped integration test is not proof of compatibility.

## Statistical interpretation

The illustrative gates are not validated alpha predictors. Selection-validation participates in selection. Repeated researcher choices across experiments can overfit even when every individual run respects its windows. The example does not estimate multiple-testing-adjusted significance, probability of backtest overfitting, capacity or expected live profitability.

## Publication boundary

This release does not include current production selection/portfolio presets, live populations or an operational trading stack. The published material teaches reusable mechanisms. It is not a reconstruction of a deployed research recipe.

from functions.functions_output import monte_carlo_summary_rows
from functions.simulation_runner import run_monte_carlo
from parameters import baseline_parameters


def main():
    result = run_monte_carlo(
        baseline_parameters,
        run_until=50,
        progress_interval=5,
        show_plot=True,
        output_path="household_returns.png",
    )
    print("\nOverall: England and Wales")
    print(f"Field visit mode: {result.params.field_visit_mode}")
    print(f"{len(result.run_seeds)} Monte Carlo runs; central 95% intervals across runs")
    print(f"{'Measure':<24} {'Mean':>12} {'95% lower':>12} {'95% upper':>12}")
    for row in monte_carlo_summary_rows(result.overall_summary):
        print(f"{row['Measure']:<24} {row['Mean']:>12.2f} {row['95% lower']:>12.2f} {row['95% upper']:>12.2f}")
    print("\nRegional results:")
    for name, values in result.region_summaries.items():
        returns = values["proportion_returned"]
        print(
            f"{name}: households {result.params.regions[name].num_households:,}; "
            f"officers {result.params.regions[name].num_field_officers}; "
            f"mean returned {values['responded_count']['mean']:.2f}; "
            f"mean returned (%) {100 * returns['mean']:.2f}; "
            f"95% interval [{100 * returns['lower_95']:.2f}, {100 * returns['upper_95']:.2f}]"
        )
    return result


if __name__ == "__main__":
    main()

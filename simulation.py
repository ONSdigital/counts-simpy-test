from functions.simulation_runner import run_simulation
from parameters import baseline_parameters


def main():
    result = run_simulation(
        baseline_parameters,
        run_until=50,
        progress_interval=5,
        show_plot=True,
        output_path="household_returns.png",
    )
    overall = result.aggregate_history
    print("\nOverall: England and Wales")
    print(
        f"Households: {overall['total_households']:,}; "
        f"returned: {overall['responded_count'][-1]:,}; "
        f"return proportion: {overall['proportion_returned'][-1]:.3f}"
    )
    print(f"Total call-centre calls: {sum(result.call_centre_history['daily_calls']):,}")
    print("\nRegional results:")
    for region in result.regions:
        history = region.return_history
        print(
            f"{region.name}: households {history['total_households']:,}; "
            f"officers {result.params.regions[region.name].num_field_officers}; "
            f"returned {history['responded_count'][-1]:,}; "
            f"return proportion {history['proportion_returned'][-1]:.3f}"
        )
    return result


if __name__ == "__main__":
    main()


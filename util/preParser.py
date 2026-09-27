import json
import random
import math
import argparse


# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------

SPEED_FACTOR_VALUES = [1, 1.5, 2]
DEFAULT_COMPUTE_NODES_PER_JOB = 2


# ------------------------------------------------------------
# Load JSON
# ------------------------------------------------------------

def load_json(input_file):
    with open(input_file, "r", encoding="utf-8") as f:
        return json.load(f)






# ------------------------------------------------------------
# Get compute nodes
# ------------------------------------------------------------

def get_compute_nodes(platform):
    """
    Compute nodes:

        is_router == false
    """

    return [
        node["id"]
        for node in platform["nodes"]
        if not node["is_router"]
    ]


# ------------------------------------------------------------
# Get router nodes
# ------------------------------------------------------------

def get_router_nodes(platform):
    """
    Router nodes:

        is_router == true
    """

    return [
        node["id"]
        for node in platform["nodes"]
        if node["is_router"]
    ]


# ------------------------------------------------------------
# Generate speed factors
# ------------------------------------------------------------

def speed_factors_by_node(compute_node_ids):
    """
    Assign one random speed factor to every compute node.

    Possible values:

        1
        1.5
        2
    """

    return {
        node_id: random.choice(SPEED_FACTOR_VALUES)
        for node_id in compute_node_ids
    }


# ------------------------------------------------------------
# Add speed factors to compute nodes
# ------------------------------------------------------------

def add_speed_factors(platform, node_speed_factors):

    for node in platform["nodes"]:

        node_id = node["id"]

        if not node["is_router"]:

            node["speed_factor"] = (
                node_speed_factors[node_id]
            )

        else:

            # Routers should not have speed_factor
            node.pop("speed_factor", None)



# ------------------------------------------------------------
# Ensure minimum compute nodes + update processing times
# ------------------------------------------------------------

def assign_compute_nodes_to_jobs(
    application,
    compute_node_ids,
    node_speed_factors,
    min_nodes_per_job
):
    if min_nodes_per_job > len(compute_node_ids):
        raise ValueError(
            f"Requested a minimum of {min_nodes_per_job} compute nodes per job, "
            f"but only {len(compute_node_ids)} compute nodes exist."
        )

    for job in application["jobs"]:
        # Preserve the number of eligible nodes, but replace stale or numeric
        # references with IDs from the current platform.
        existing_count = len(job.get("can_run_on", []))

        if existing_count < min_nodes_per_job:
            needed_count = min_nodes_per_job - existing_count
            target_count = existing_count + needed_count
        else:
            target_count = existing_count

        if target_count > len(compute_node_ids):
            raise ValueError(
                f"Job {job['id']} requires {target_count} compute nodes, but "
                f"only {len(compute_node_ids)} are available."
            )

        # random.sample returns distinct IDs from the platform, so this field
        # always has the platform's node-ID type (for example, strings).
        job["can_run_on"] = random.sample(compute_node_ids, target_count)


# ------------------------------------------------------------
# Process complete file
# ------------------------------------------------------------

def process_file(
    input_file,
    output_file,
    nodes_per_job
):

    # --------------------------------------------------------
    # Load
    # --------------------------------------------------------

    data = load_json(input_file)

    platform = data["platform"]
    application = data["application"]


    # --------------------------------------------------------
    # 3. Get compute/router nodes
    # --------------------------------------------------------

    compute_node_ids = get_compute_nodes(
        platform
    )

    router_node_ids = get_router_nodes(
        platform
    )

    # --------------------------------------------------------
    # 4. Generate speed factors
    # --------------------------------------------------------

    node_speed_factors = speed_factors_by_node(
        compute_node_ids
    )

    # --------------------------------------------------------
    # 5. Add speed factors
    # --------------------------------------------------------

    add_speed_factors(
        platform,
        node_speed_factors
    )

    # --------------------------------------------------------
    # 6. Assign compute nodes to jobs
    #    and calculate processing times
    # --------------------------------------------------------

    assign_compute_nodes_to_jobs(
        application,
        compute_node_ids,
        node_speed_factors,
        nodes_per_job
    )

    # --------------------------------------------------------
    # 7. Save
    # --------------------------------------------------------

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            indent=4
        )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print()
    print("========================================")
    print("JSON generation completed")
    print("========================================")
    print(f"Input file           : {input_file}")
    print(f"Output file          : {output_file}")
    print(
        f"Total platform nodes : "
        f"{len(platform['nodes'])}"
    )
    print(
        f"Compute nodes        : "
        f"{len(compute_node_ids)}"
    )
    print(
        f"Router nodes         : "
        f"{len(router_node_ids)}"
    )
    print(
        f"Compute nodes/job    : "
        f"{nodes_per_job}"
    )
    print(
        f"Jobs                 : "
        f"{len(application['jobs'])}"
    )

    if "links" in platform:
        print(
            f"Links                : "
            f"{len(platform['links'])}"
        )

    print("========================================")
    print()


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Generate scheduling JSON with sequential "
            "node IDs, updated links, random job mappings, "
            "speed factors and processing times."
        )
    )

    parser.add_argument(
        "input",
        help="Input JSON file"
    )

    parser.add_argument(
        "-o",
        "--output",
        default="generated_input.json",
        help=(
            "Output JSON file "
            "(default: generated_input.json)"
        )
    )

    parser.add_argument(
        "-n",
        "--nodes-per-job",
        type=int,
        default=DEFAULT_COMPUTE_NODES_PER_JOB,
        help=(
            "Number of compute nodes assigned "
            "to each job (default: 2)"
        )
    )

    args = parser.parse_args()

    if args.nodes_per_job < 1:
        parser.error(
            "--nodes-per-job must be at least 1"
        )

    process_file(
        args.input,
        args.output,
        args.nodes_per_job
    )


if __name__ == "__main__":
    main()
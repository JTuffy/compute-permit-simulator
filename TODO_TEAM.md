# Team TODO — Apart Sprint (Jan 30 – Feb 1)
> Reference documents: `source/`

---
Question

* Why Pydantic? Would writing a typed library be easier, avoid doubling up definitions across schemas.py and the rest of the files?
* Should we start by redefining penalties, etc, as dollar values (in millions)? It would make it easier to compare to real-world data.


High Priority

* Review example Mesa projects for inspiration/code structure
    * https://github.com/Wisaacj/mesa-auctions
    * https://github.com/jofmi/TvsP_ABM
* (Josh) build out infrastructure/ modules. Breakdown:
    * ensure interface with Mesa works well
    * check functionality for collection data on simulations
    * basic visualisation
* [x] Create tests/ directory
* [x] Basic test that agents cheat if the inequality condition is met
* [x] (Emlyn) check, fix and expand domain/ modules to match the model discussed with team (to be broken into smaller tasks)
* [x] Add pytest to Makefile (Added to pyproject.toml / uv)
* [x] Add GitHub Actions CI (ruff + pytest)
* [ ] Add test to check highest value agents get permits
* [ ] Implement Deterrence Model Refinements (Thresholds, Dynamic Rep, Backchecks)
* [ ] Verify Scenarios: Compliance Transition, High Stakes, Backcheck Safety, Reputation Cascade
* [ ] Check zero-enforcement scenario p=0
* [ ] Check behaviour for compliance rate, undetected risk, audit hit rate, welfare proxy

Medium Priority

* [ ] Expected behaviour test: cheating decreases as p increases
* [ ] Expected behaviour test: Check Joel's paper for examples
* [ ] Add parameter sweep config based on Sue's document
* [ ] Docstrings for public functions (good one for AI tool to do for us)
* [x] Model specification doc (Merged into technical specification)
* [ ] Add deterministic simulation works with seed, and write matching test
# CLI conversion

1. select.py --protection-level pr_any --classes A,GA,FA [--keep-discrete] [--attrfile attrnames.txt] --output outputfile.tab file1.tab file2.tab

2. cluster_score.py --upper_mean 0.9 --lower_mean 0.7 --upper_value FA --lower_value GA --cDonaldsC 5 --column_name mycol --output outputfile.tab infile.tab

3. mars_scores.py --learners constmarses --only_run structure,community --training_sample 0.25  # TODO: determine output formats

4. metamars.py  # (and beyond)
## Utils
 * concatenate.py --trim_per 10000 --trim_total 10000 --no_random --output outputfile.tab file1.tab file2.tab
 * decorrelate.py --corr_min 0.01 --corr_max 0.99 single_file.tab

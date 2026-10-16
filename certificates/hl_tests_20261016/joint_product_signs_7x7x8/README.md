# Compensated product signs for the7x7x8 tensor

This separate variant preserves ordinary input/output coordinates and279 products. It changes individual input-form signs and compensates the corresponding W columns, so it is not a result for the original57 fixed maps.

The literal counts are U273,V334,W572:1179 additions,1458 scalar operations including products. The nineteen fixed-map rows retain their own counts. `verify_joint_product_signs.py` at the bundle root checks every circuit, the exact row/column sign relation to the original maps, and the complete multiplication tensor.

`input_candidates/` preserves the original signed DAGs passed to the existing public joint orientation method. From the bundle root, run `python3 joint_product_signs_7x7x8/reproduce_joint_signs.py --methods METHODS_LINEAR --out rerun_joint_signs --seconds 10`, where METHODS_LINEAR is the public repository's methods/linear directory. OR-Tools is required only to repeat the orientation; certificate verification uses the standard library.

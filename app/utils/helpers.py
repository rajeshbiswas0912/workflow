def clean_out_row(row) -> dict:
    return {k.removeprefix("out_"): v for k, v in row.items()}

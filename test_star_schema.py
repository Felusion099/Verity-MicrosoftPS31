import sys
sys.path.insert(0, '.')
from src import data_generator
import traceback

try:
    from src import data_generator
    import numpy as np
    from datetime import date
    
    rng = np.random.default_rng(42)
    date_dim = data_generator._build_date_dim(
        date.fromisoformat('2024-01-01'), 
        date.fromisoformat('2026-09-14')
    )
    product_dim = data_generator._build_product_dim(np.random.default_rng(42))
    customer_dim = data_generator._build_customer_dim(np.random.default_rng(42))
    territory_dim = data_generator._build_territory_dim()
    
    rng = np.random.default_rng(42)
    date_dim = data_generator._build_date_dim(
        date.fromisoformat('2024-01-01'), 
        date.fromisoformat('2026-09-14')
    )
    product_dim = data_generator._build_product_dim(np.random.default_rng(42))
    customer_dim = data_generator._build_customer_dim(np.random.default_rng(42))
    territory_dim = data_generator._build_territory_dim()
    
    fact_clean = data_generator._generate_fact(rng, date_dim, product_dim, customer_dim)
    raw = data_generator._inject_dirty_data(fact_clean, np.random.default_rng(42))
    
    dims = {
        'date': date_dim, 
        'product': product_dim,
        'customer': customer_dim, 
        'territory': territory_dim
    }
    
    print('Testing _build_star_schema...')
    try:
        result = data_generator._build_star_schema(
            np.random.default_rng(42), 
            date_dim, 
            product_dim, 
            customer_dim, 
            territory_dim, 
            data_generator._inject_dirty_data(
                data_generator._generate_fact(np.random.default_rng(42), 
                    data_generator._build_date_dim(date.fromisoformat('2024-01-01'), date.fromisoformat('2026-09-14')),
                    data_generator._build_product_dim(np.random.default_rng(42)),
                    data_generator._build_customer_dim(np.random.default_rng(42))
                ),
                np.random.default_rng(42)
            ),
            dims
        )
        print(f'Result keys: {list(result.keys())}')
        print(f'fact_rows: {result.get("fact_rows")}')
        print(f'finance_plan_rows: {result.get("finance_plan_rows")}')
    except Exception as e:
        import traceback
        traceback.print_exc()
except Exception as e:
    traceback.print_exc()
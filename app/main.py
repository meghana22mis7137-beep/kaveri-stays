from app.db import get_connection_string
from app.errors import explain

print(get_connection_string())
print(explain(409))
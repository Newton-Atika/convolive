import os, sys

print("🔧 DEBUG STARTUP")
print("ENV PORT =", os.environ.get("PORT"))
print("Procfile exists:", os.path.exists("Procfile"))
print("Full cmd:", sys.argv)

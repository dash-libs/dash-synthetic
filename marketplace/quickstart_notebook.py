# Databricks notebook source
# MAGIC %md
# MAGIC # dash-synthetic — Synthetic Data
# MAGIC
# MAGIC Generate privacy-safe synthetic data from real Databricks tables.
# MAGIC
# MAGIC **Install and launch:**

# COMMAND ----------

# MAGIC %pip install dash-synthetic

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

import dashsynthetic
dashsynthetic.launch()

# COMMAND ----------
# MAGIC %md
# MAGIC ## Python API (optional — for automation)
# MAGIC
# MAGIC ```python
# MAGIC import dashsynthetic
# MAGIC # See docs/api/ for full API reference
# MAGIC ```

Operators
=========

The differences between Spark and Hive operators could be categorized into the following types:

Supported Operators
---------------------

.. note::
   :class: margin

   - **<->**: Bi-directional compatibility
   - **->**: A Spark workload can run the same way in Hive, but not vice versa
   - **<-**: A Hive workload can run the same way in Spark, but not vice versa
   - **!=**: Non-compatible

.. list-table:: The differences between Spark and Hive Operators
   :widths: auto
   :align: center
   :header-rows: 1

   * - Operator
     - Spark
     - Hive
     - Compatible
     - Description
     - Differences
   * - `+`
     - Y
     - Y
     - <-
     - addition
     - | See `Handle Arithmetic Overflow`_
       | See `Allows Interval Input`_

.. _Handle Arithmetic Overflow: spark_vs_hive_functions.html#handle-arithmetic-overflow
.. _Allows Interval Input: spark_vs_hive_functions.html#allows-interval-input
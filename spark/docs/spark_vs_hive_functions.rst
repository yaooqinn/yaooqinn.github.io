Functions
=========

The differences between Spark and Hive functions could be categorized into the following types:


.. list-table:: The differences between Spark and Hive functions
   :widths: auto
   :align: center
   :header-rows: 1

   * - Function
     - Spark
     - Hive
     - Compatible
     - Description
     - Differences
   * - `DECODE`_ (bin, charset)
     - Y
     - Y
     - N
     - Decodes the first argument using the second argument character set
     -
       - `bin`: The byte array to be decoded
         - Spark supports both string and binary values, while Hive supports only binary type
       - `charset`: The character set to use for decoding
         - Spark 3.x and previous versions and Hive support all the character sets that are supported by Java, while the charsets is limited to 'US-ASCII', 'ISO-8859-1', 'UTF-8', 'UTF-16BE', 'UTF-16LE', 'UTF-16' since Spark 4.0
       - Output for malformed input:
         - Spark produces mojibake(nonsense characters), while hive raises an error for case like `DECODE(X'E58A9DE5909B', 'US-ASCII')`
   * - DECODE(expr, search, result [, search, result ] ... [, default])
     - Y
     - N
     - N
     - Compares expr to each search value in order. If expr is equal to a search value, decode returns the corresponding result. If no match is found, then it returns default. If default is omitted, it returns null.
     - The Spark version is derived from `Oracle DECODE`_, while Hive does not have it.
   * - `ENCODE`_ (str, charset)
     - Y
     - Y
     - N
     - Encode the first argument using the second argument character set
     -
       - `str`: The string to be decoded
         - Spark supports any type of values that can be implicitly converted to string, while Hive supports only string type
       - `charset`: The character set to use for decoding
         - Spark 3.x and previous versions and Hive support all the character sets that are supported by Java, while the charsets is limited to 'US-ASCII', 'ISO-8859-1', 'UTF-8', 'UTF-16BE', 'UTF-16LE', 'UTF-16' since Spark 4.0
       - Output for malformed input:
         - Spark produces mojibake(nonsense characters), while Hive raises an error for case like `ENCODE('abc中', 'US-ASCII')`
   * - `GREATEST`_ (expr, ...)
     - Y
     - Y
     - N
     - Returns the greatest value of all parameters
     -
       - `expr`: The expression to compare
         - Spark and Hive(< 2.0.0) require all of them having the data type, while strict type restriction relaxed in Hive(> 2.0.0)
       - Output for NULL:
         - Spark and Hive(< 2.0.0) skip NULLs, while Hive(> 2.0.0) returns NULL if any of the parameters are NULL
   * - `LEAST`_ (expr, ...)
     - Y
     - Y
     - N
     - Returns the least value of all parameters
     - The differences are as same as GREATEST



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

.. _ENCODE: https://spark.apache.org/docs/latest/api/sql/index.html#encode
.. _DECODE: https://spark.apache.org/docs/latest/api/sql/index.html#decode
.. _Oracle DECODE: https://docs.oracle.com/en/database/oracle/oracle-database/23/sqlrf/DECODE.html
.. _GREATEST: https://spark.apache.org/docs/latest/api/sql/index.html#greatest
.. _LEAST: https://spark.apache.org/docs/latest/api/sql/index.html#least

Functions
=========


.. list-table:: Frozen Delights!
   :widths: auto
   :align: center
   :header-rows: 1

   * - Function
     - Spark
     - Hive
     - Compatible
     - Description
     - Differences
   * - `DECODE(str, charset)`
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
         - Spark produces mojibake(nonsense charactor), while hive raises an error for case like `ENCODE('abc中', 'US-ASCII')`
   * - GREATEST
     - ✓
     - ✓
     - ×
     - TBD
     - TBD
   * - LEAST
     - ✓
     - ✓
     - ×
     - TBD
     - TBD



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
Functions
=========

The differences between Spark and Hive functions could be categorized into the following types:

Compatibility Details
---------------------

.. note::
   :class: margin

   - **<->**: Bi-directional compatibility
   - **->**: A Spark workload can run the same way in Hive, but not vice versa
   - **<-**: A Hive workload can run the same way in Spark, but not vice versa
   - **!=**: Non-compatible

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
   * - `ABS`_ (expr)
     - Y
     - Y
     - <-
     - Returns the absolute value of the numeric value
     - | See `Handle Arithmetic Overflow`_
       | See `Allows Interval Input`_
   * - `BIN`_ (expr)
     - Y
     - Y
     - <->
     - Returns the number in binary format
     -
   * - `DECODE`_ (bin, charset)
     - Y
     - Y
     - !=
     - Decodes the first argument using the second argument character set
     -
       - `bin`: The byte array to be decoded
         - Spark supports both string and binary values, while Hive supports only binary type
       - `charset`: The character set to use for decoding
         - Spark 3.x and previous versions and Hive support all the character sets that are supported by Java, while the charsets is limited to 'US-ASCII', 'ISO-8859-1', 'UTF-8', 'UTF-16BE', 'UTF-16LE', 'UTF-16' since Spark 4.0
       - Output for malformed input:
         - Spark produces mojibake(nonsense characters), while hive raises an error for case like `DECODE(X'E58A9DE5909B', 'US-ASCII')`
   * - `DECODE`_ (expr, search, result [, search, result ] ... [, default])
     - Y
     - **N**
     - !=
     - Compares expr to each search value in order. If expr is equal to a search value, decode returns the corresponding result. If no match is found, then it returns default. If default is omitted, it returns null.
     - The Spark version is derived from `Oracle DECODE`_, while Hive does not have it.
   * - `E`_ ()
     - Y
     - Y
     - <->
     - Returns the value of the base of the natural logarithm
     -
   * - `ENCODE`_ (str, charset)
     - Y
     - Y
     - !=
     - Encode the first argument using the second argument character set
     -
       - `str`: The string to be decoded
         - Spark supports any type of values that can be implicitly converted to string, while Hive supports only string type
       - `charset`: The character set to use for decoding
         - Spark 3.x and previous versions and Hive support all the character sets that are supported by Java, while the charsets is limited to 'US-ASCII', 'ISO-8859-1', 'UTF-8', 'UTF-16BE', 'UTF-16LE', 'UTF-16' since Spark 4.0
       - Output for malformed input:
         - Spark produces mojibake(nonsense characters), while Hive raises an error for case like `ENCODE('abc中', 'US-ASCII')`
   * - `FACTORIAL`_ (expr)
     - Y
     - Y
     - !=
     - Returns the factorial of `expr`. `expr` is [0..20]. Otherwise, null.
     - Spark supports not only integral types, such as tinyint, smallint, int, bigint, but also fractional types(weird right?), while Hive supports only integral types
   * - `GREATEST`_ (expr, ...)
     - Y
     - Y
     - !=
     - Returns the greatest value of all parameters
     -
       - `expr`: The expression to compare
         - Spark and Hive(< 2.0.0) require all of them having the data type, while strict type restriction relaxed in Hive(> 2.0.0)
       - Output for NULL:
         - Spark and Hive(< 2.0.0) skip NULLs, while Hive(> 2.0.0) returns NULL if any of the parameters are NULL
   * - `HASH`_ (expr, ...)
     - Y
     - Y
     - !=
     - Returns a hash value of the arguments
     - As Spark and Hive use different hash algorithms, the results are not the same for the same input.
   * - `LEAST`_ (expr, ...)
     - Y
     - Y
     - !=
     - Returns the least value of all parameters
     - The differences are as same as GREATEST
   * - `NEGATIVE`_ (expr)
     - Y
     - Y
     - N
     - Returns the negated value of `expr`.
     - | See `Handle Arithmetic Overflow`_
       | See `Allows Interval Input`_
   * - `POSITIVE`_ (expr)
     - Y
     - Y
     - <-
     - Returns the value of the argument
     - See `Allows Interval Input`_
   * - `PI`_ ()
     - Y
     - Y
     - <->
     - Returns the value of PI
     -

Generic Differences
-------------------

Handle Arithmetic Overflow
~~~~~~~~~~~~~~~~~~~~~~~~~~

An arithmetic overflow occurs when a calculation exceeds the maximum size that can be stored in the data type being used.

.. note::
   :class: margin, dropdown, toggle

   When `spark.sql.ansi.enabled` is set to `false`, which is default to `false` before Spark 4.0.0 and `true` since 4.0.0.
   Spark uses this semantics to handle overflow in most of the arithmetic operations.

.. code-block:: sql
   :Caption: **Produces overflowed values**
   :emphasize-lines: 1
   :class: dropdown, toggle

   > SELECT 127Y + 1Y
   -128

.. note::
   :class: margin, dropdown, toggle

   - When `spark.sql.ansi.enabled` is set to `false`, which is default to `false` before Spark 4.0.0 and `true` since 4.0.0.
     Spark uses this semantics to handle overflow in some of the arithmetic operations.
   - Spark provides some `try_` prefixed variants of the original functions to handle overflow with NULL output in arithmetic operations, e.g. `try_add` v.s. `add`.

.. code-block:: sql
   :Caption: **Produces `NULL`**
   :emphasize-lines: 1
   :class: dropdown, toggle

   > SELECT try_add(127Y, 1Y)
   NULL

.. note::
   :class: margin, dropdown, toggle

   When `spark.sql.ansi.enabled` is set to `true`, which is default to `false` before Spark 4.0.0 and `true` since 4.0.0.
   Spark uses this semantics to handle overflow in arithmetic operations.

.. code-block:: sql
   :Caption: **Throws Errors**
   :emphasize-lines: 1
   :class: dropdown, toggle

   > SELECT 127Y + 1Y
   org.apache.spark.SparkArithmeticException: [BINARY_ARITHMETIC_OVERFLOW] 127S + 1S caused overflow. SQLSTATE: 22003

.. note::
   :class: margin, dropdown, toggle

   Hive uses this semantics to handle overflow in arithmetic operations.

.. code-block:: sql
   :Caption: **Widens data type**
   :emphasize-lines: 1
   :class: dropdown, toggle

   > SELECT 127Y + 1Y
   -- The result type is promoted from tinyint to smallint
   128

Handle NULL Input
~~~~~~~~~~~~~~~~~

Allows Interval Input
~~~~~~~~~~~~~~~~~~~~~

- Spark allows interval types as input most of the arithmetic operations, e.g. `ABS`, `POSITIVE`, and `NEGATIVE` functions, while Hive does not.

.. code-block:: sql
   :Caption: **Examples**
   :emphasize-lines: 1
   :class: dropdown, toggle

   > SELECT ABS(- INTERVAL 1-1 YEAR TO MONTH)
   INTERVAL 1-1 YEAR TO MONTH


.. _ABS: https://spark.apache.org/docs/latest/api/sql/index.html#abs
.. _BIN: https://spark.apache.org/docs/latest/api/sql/index.html#bin
.. _DECODE: https://spark.apache.org/docs/latest/api/sql/index.html#decode
.. _E: https://spark.apache.org/docs/latest/api/sql/index.html#e
.. _ENCODE: https://spark.apache.org/docs/latest/api/sql/index.html#encode
.. _FACTORIAL: https://spark.apache.org/docs/latest/api/sql/index.html#factorial
.. _Oracle DECODE: https://docs.oracle.com/en/database/oracle/oracle-database/23/sqlrf/DECODE.html
.. _GREATEST: https://spark.apache.org/docs/latest/api/sql/index.html#greatest
.. _HASH: https://spark.apache.org/docs/latest/api/sql/index.html#hash
.. _NEGATIVE:  https://spark.apache.org/docs/latest/api/sql/index.html#negative
.. _LEAST: https://spark.apache.org/docs/latest/api/sql/index.html#least
.. _POSITIVE: https://spark.apache.org/docs/latest/api/sql/index.html#positive
.. _PI: https://spark.apache.org/docs/latest/api/sql/index.html#pi

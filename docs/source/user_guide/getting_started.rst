Getting Started
===============

The sections below provide a high level overview of the ``Autoimpute`` package. This page takes you through installation, dependencies, main features, imputation methods supported, and basic usage of the package. It also provides links to get in touch with the authors, review our lisence, and review how to contribute.

Installation
------------


* Download ``Autoimpute`` with ``pip install autoimpute``. 
* If ``pip`` cached an older version, try ``pip install --no-cache-dir --upgrade autoimpute``.
* If you want to work with the development branch, use the script below:

*Development*

.. code-block:: sh

   git clone -b dev --single-branch https://github.com/kearnz/autoimpute.git
   cd autoimpute
   python setup.py install

Versions and Dependencies
-------------------------


* Python 3.8+
* Dependencies:

  * ``numpy``
  * ``scipy``
  * ``pandas``
  * ``statsmodels``
  * ``scikit-learn``
  * ``xgboost``
  * ``pymc``
  * ``seaborn``
  * ``missingno``

*A note for Windows Users*\ :

* Autoimpute 0.13.0+ has not been tested on windows and can't verify support for pymc. Historically we've had some issues with pymc on windows.
* Autoimpute works on Windows but users may have trouble with pymc for bayesian methods. `(See discourse) <https://discourse.pymc.io/t/an-error-message-about-cant-pickle-fortran-objects/1073>`_
* Users may receive a runtime error ``‘can’t pickle fortran objects’`` when sampling using multiple chains.
* There are a couple of things to do to try to overcome this error:

  * Reinstall theano and pymc. Make sure to delete .theano cache in your home folder.
  * Upgrade joblib in the process, which is reponsible for generating the error (pymc uses joblib under the hood).
  * Set ``cores=1`` in ``pm.sample``. This should be a last resort, as it means posterior sampling will use 1 core only. Not using multiprocessing will slow down bayesian imputation methods significantly.

* Reach out and let us know if you've worked through this issue successfully on Windows and have a better solution!

Main Features
-------------


* Utility functions and basic visualizations to explore missingness patterns
* Missingness classifier and automatic missing data test set generator
* Native handling for categorical variables (as predictors and targets of imputation)
* Single and multiple imputation classes for ``pandas`` ``DataFrames``
* Analysis methods and pooled parameter inference using multiply imputed datasets
* Numerous imputation methods, as specified in the table below:

Imputation Methods Supported
----------------------------

.. list-table::
   :header-rows: 1

   * - Univariate
     - Multivariate
     - Time Series / Interpolation
   * - Mean
     - Linear Regression
     - Linear 
   * - Median
     - Binomial Logistic Regression
     - Quadratic 
   * - Mode
     - Multinomial Logistic Regression
     - Cubic
   * - Random
     - Stochastic Regression
     - Polynomial
   * - Norm
     - Bayesian Linear Regression
     - Spline
   * - Categorical
     - Bayesian Binary Logistic Regression
     - Time-weighted
   * - 
     - Predictive Mean Matching
     - Next Obs Carried Backward
   * - 
     - Local Residual Draws
     - Last Obs Carried Forward

Example Usage
-------------

Autoimpute is designed to be user friendly and flexible. When performing imputation, Autoimpute fits directly into ``scikit-learn`` machine learning projects. Imputers inherit from sklearn's ``BaseEstimator`` and ``TransformerMixin`` and implement ``fit`` and ``transform`` methods, making them valid Transformers in an sklearn pipeline.

Right now, there are two ``Imputer`` classes we'll work with:

.. code-block:: python

	from autoimpute.imputations import SingleImputer, MultipleImputer, MiceImputer
	si = SingleImputer() # pass through data once
	mi = MultipleImputer() # pass through data multiple times
	mice = MiceImputer() # pass through data multiple times and iteratively optimize imputations in each column

Imputations can be as simple as:

.. code-block:: python

   # simple example using default instance of MiceImputer
   imp = MiceImputer()

   # fit transform returns a generator by default, calculating each imputation method lazily
   imp.fit_transform(data)

Or quite complex, such as:

.. code-block:: python

   # create a complex instance of the MiceImputer
   # Here, we specify strategies by column and predictors for each column
   # We also specify what additional arguments any `pmm` strategies should take
   imp = MiceImputer(
       n=10,
       strategy={"salary": "pmm", "gender": "bayesian binary logistic", "age": "norm"},
       predictors={"salary": "all", "gender": ["salary", "education", "weight"]},
       imp_kwgs={"pmm": {"fill_value": "random"}},
       visit="left-to-right",
       return_list=True
   )

   # Because we set return_list=True, imputations are done all at once, not evaluated lazily.
   # This will return M*N, where M is the number of imputations and N is the size of original dataframe.
   imp.fit_transform(data)

Autoimpute also extends supervised machine learning methods from ``scikit-learn`` and ``statsmodels`` to apply them to multiply imputed datasets (using the ``MiceImputer`` under the hood). Right now, Autoimpute supports linear regression and binary logistic regression. Additional supervised methods are currently under development.

As with Imputers, Autoimpute's analysis methods can be simple or complex:

.. code-block:: python

   from autoimpute.analysis import MiLinearRegression

   # By default, use statsmodels OLS and MiceImputer()
   simple_lm = MiLinearRegression()

   # fit the model on each multiply imputed dataset and pool parameters
   simple_lm.fit(X_train, y_train)

   # get summary of fit, which includes pooled parameters under Rubin's rules
   # also provides diagnostics related to analysis after multiple imputation
   simple_lm.summary()

   # make predictions on a new dataset using pooled parameters
   predictions = simple_lm.predict(X_test)

   # Control both the regression used and the MiceImputer itself
   multiple_imputer_arguments = dict(
       n=3,
       strategy={"salary": "pmm", "gender": "bayesian binary logistic", "age": "norm"},
       predictors={"salary": "all", "gender": ["salary", "education", "weight"]},
       imp_kwgs={"pmm": {"fill_value": "random"}},
       scaler=StandardScaler(),
       visit="left-to-right",
       verbose=True
   )
   complex_lm = MiLinearRegression(
       model_lib="sklearn", # use sklearn linear regression
       mi_kwgs=multiple_imputer_arguments # control the multiple imputer
   )

   # fit the model on each multiply imputed dataset
   complex_lm.fit(X_train, y_train)

   # get summary of fit, which includes pooled parameters under Rubin's rules
   # also provides diagnostics related to analysis after multiple imputation
   complex_lm.summary()

   # make predictions on new dataset using pooled parameters
   predictions = complex_lm.predict(X_test)

Note that we can also pass a pre-specified ``MiceImputer`` to either analysis model instead of using ``mi_kwgs``. The option is ours, and it's a matter of preference. If we pass a pre-specified ``MiceImputer``\ , anything in ``mi_kwgs`` is ignored, although the ``mi_kwgs`` argument is still validated.

.. code-block:: python

   from autoimpute.imputations import MiceImputer
   from autoimpute.analysis import MiLinearRegression

   # create a multiple imputer first
   custom_imputer = MiceImputer(n=3, strategy="pmm", return_list=True)

   # pass the imputer to a linear regression model
   complex_lm = MiLinearRegression(mi=custom_imputer, model_lib="statsmodels")

   # proceed the same as the previous examples
   complex_lm.fit(X_train, y_train).predict(X_test)
   complex_lm.summary()

For a deeper understanding of how the package works and its features, see our `tutorials website <https://kearnz.github.io/autoimpute-tutorials/>`_.

Creators and Maintainers
------------------------


* Joseph Kearney – `@kearnz <https://github.com/kearnz>`_
* Shahid Barkat - `@shabarka <https://github.com/shabarka>`_

See the `Authors <https://github.com/kearnz/autoimpute/blob/master/AUTHORS.rst>`_ page to get in touch!

License
-------

Distributed under the MIT license. See `LICENSE <https://github.com/kearnz/autoimpute/blob/master/LICENSE>`_ for more information.

Contributing
------------

Guidelines for contributing to our project. See `CONTRIBUTING <https://github.com/kearnz/autoimpute/blob/master/CONTRIBUTING.md>`_ for more information.

Contributor Code of Conduct
---------------------------

Adapted from Contributor Covenant, version 1.0.0. See `Code of Conduct <https://github.com/kearnz/autoimpute/blob/master/CODE_OF_CONDUCT.md>`_ for more information.

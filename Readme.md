# Abaca API

This document describes some useful commands and procedures for the Abaca API.

## Setup Autocompletion on VSCode

In order to get autocompletion on VSCode you need to setup a virtual environment, for that you just need to run the following command:

```shell
python3 -m venv .venv
```

Now, you need to select the Python interpreter on VSCode, a list will be presented with various options, you must choose the one that point to the `./.venv` folder.

To finalize, on the project folder run the `pip install -r requirements.in` command to install all the project dependencies.

## Algorithm Calculator

There is a Matching Algorithm calculator accessible at `/admin/matching/matchingalgorithms/calculator/` that was developed externaly as an SPA (source code is in the `../algorithm-calculator` directory) and later integrated into the Django Admin panel.

The built assets for this calculator are the `static/css/algorithm-calculator.css` and `static/js/algorithm-calculator.js` files. Please refer to the [calculator's project README file](https://github.com/Pixelmatters/abaca-app/blob/develop/algorithm-calculator/README.md) for instructions on how to update them.

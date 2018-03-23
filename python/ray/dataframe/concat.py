import pandas as pd
import numpy as np
from ray import dataframe as rdf
from .utils import (
    from_pandas,
    _deploy_func)
from functools import reduce


def concat(objs, axis=0, join='outer', join_axes=None, ignore_index=False,
           keys=None, levels=None, names=None, verify_integrity=False,
           copy=True):

    def _concat(frame1, frame2):
        # Check type on objects
        # Case 1: Both are Pandas DF
        if isinstance(frame1, pd.DataFrame) and \
           isinstance(frame2, pd.DataFrame):

            return pd.concat((frame1, frame2), axis, join, join_axes,
                             ignore_index, keys, levels, names,
                             verify_integrity, copy)

        # Case 2: Both are different types
        if isinstance(frame1, pd.DataFrame):
            frame1 = from_pandas(frame1, len(frame1) / 2**16 + 1)
        if isinstance(frame2, pd.DataFrame):
            frame2 = from_pandas(frame2, len(frame2) / 2**16 + 1)

        # Case 3: Both are Ray DF
        if isinstance(frame1, rdf.DataFrame) and \
           isinstance(frame2, rdf.DataFrame):

            new_columns = frame1.columns.join(frame2.columns, how=join)

            def remove_columns(pdf):
                return pdf[new_columns]

            def add_columns(pdf):
                print("TYPE:", type(pdf))
                return pdf.reindex(columns=new_columns)

            if axis in [0, 'index', 'rows']:
                if join == 'inner':
                    new_f1 = [_deploy_func.remote(remove_columns, part) for
                              part in frame1._df]
                    new_f2 = [_deploy_func.remote(remove_columns, part) for
                              part in frame2._df]

                    return rdf.DataFrame(new_f1 + new_f2, columns=new_columns,
                                         index=frame1.index.append(
                                                                 frame2.index))

                elif join == 'outer':
                    new_f1 = [_deploy_func.remote(add_columns, part) for
                              part in frame1._df]
                    new_f2 = [_deploy_func.remote(add_columns, part) for
                              part in frame2._df]

                    return rdf.DataFrame(new_f1 + new_f2, columns=new_columns,
                                         index=frame1.index.append(
                                                                 frame2.index))
            else:
                raise NotImplementedError(
                      "Concat not implemented for axis=1. To contribute to "
                      "Pandas on Ray, please visit github.com/ray-project/ray."
                      )

    # (TODO) Group all the pandas dataframes

    if isinstance(objs, dict):
        raise NotImplementedError(
              "Obj as dicts not implemented. To contribute to "
              "Pandas on Ray, please visit github.com/ray-project/ray."
              )

    all_pd = np.all([isinstance(obj, pd.DataFrame) for obj in objs])
    if all_pd:
        result = pd.concat(objs, axis, join, join_axes,
                           ignore_index, keys, levels, names,
                           verify_integrity, copy)
    else:
        result = reduce(_concat, objs)

    if isinstance(result, pd.DataFrame):
        return from_pandas(result, len(result) / 2**16 + 1)

    return result

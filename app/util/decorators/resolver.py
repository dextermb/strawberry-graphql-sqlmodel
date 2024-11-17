import inspect
import strawberry
import typing as t
import sqlmodel as db

from sqlmodel.main import FieldInfo
from sqlmodel.sql.expression import SelectOfScalar


class BaseComparisonInputType:
  lt: t.Any
  gt: t.Any
  lte: t.Any
  gte: t.Any
  like: t.Any


class InputField:
  """
  Change the behaviour of how the input field can be queried:
    - lt: Less Than
    - gt: Greater Than
    - lte: Less Than or Equal To
    - gte: Greater Than or Equal To
    - like: Wildcard search to contain subvalue
    - list: Allows for a list of variables to be provided
    - required: Must be provided
  """
  def __init__(self, *, lt = False, gt = False, lte = False, gte = False, like = False, list = False, required = False):
    self.lt = lt
    self.gt = gt
    self.lte = lte
    self.gte = gte
    self.like = like
    self.list = list
    self.required = required

  def __getitem__(self, key: str):
    attributes = vars(self)

    if key not in attributes:
        raise KeyError(f"'{key}' not found in instance attributes")

    return attributes[key]

  @property
  def needs_comparison_input(self):
    return self.lt or self.gt or self.lte or self.gte or self.like

  @property
  def comparison_types(self) -> dict[str, bool]:
    return { "lt": self.lt, "gt": self.gt, "lte": self.lte, "gte": self.gte, "like": self.like}

  # Generate a dynamic Strawberry input type class.
  @classmethod
  def create_input_type(cls, class_name: str, fields: dict[str, t.Any]):
    annotations = {f: t for f, t in fields.items()}
    namespace = {
      '__annotations__': annotations,
      **{f: None for f in fields}
    }

    cls = type(class_name, (), namespace)

    return strawberry.input(cls)

  @classmethod
  def create_stmt_where_clauses(cls, *, stmt: SelectOfScalar, database_field: FieldInfo, resolver_input: t.Any) -> SelectOfScalar:
    equals = getattr(resolver_input, "equals")

    # Exit early if comparison is basic
    if equals is not None:
      return stmt.where(database_field == equals)

    comparisons: BaseComparisonInputType|None = getattr(resolver_input, "comparison")

    if comparisons is None:
      return stmt

    clauses = []

    """
    Go through each of the complex comparisons and append to
    the clauses sequence, then spread the sequence into an
    `and_` to group the where clauses.
    """

    if hasattr(comparisons, "lt") and comparisons.lt is not None:
      clauses.append(database_field < comparisons.lt)

    if hasattr(comparisons, "gt") and comparisons.gt is not None:
      clauses.append(database_field > comparisons.gt)

    if hasattr(comparisons, "lte") and comparisons.lte is not None:
      clauses.append(database_field <= comparisons.lte)

    if hasattr(comparisons, "gte") and comparisons.gte is not None:
      clauses.append(database_field >= comparisons.gte)

    if hasattr(comparisons, "like") and comparisons.like is not None:
      clauses.append(db.col(database_field).ilike(comparisons.like))

    return stmt.where(db.and_(*clauses))

  """
  Generate a dynamic annotation based on the original database type:
    1. Deterime if a list can be provided
    2. Determine if field is required
    3. Deterime if a comparison input is required
      3a. Dynamically generate the comparison input type
      3b. Dynamically generate the top-level input type
      3c. Deterime if the input type should be required
    4. Return either basic annotation or input type class
  """
  def annotation(self, *, class_prefix: str, base_annotation):
    annotation = base_annotation

    if self.list == True:
      annotation = t.List[annotation]

    if self.required == False:
      annotation = t.Optional[annotation]

    if self.needs_comparison_input == True:
      ComparisonInput = InputField.create_input_type(
        class_prefix+ "_" +"ComparisonInput",
        # Pull comparison types (eg. lt) and attach original annotation
        {f: base_annotation for f, b in self.comparison_types.items() if b}
      )

      TopLevelInput = InputField.create_input_type(
        class_prefix+ "_" +"TopLevelInput",
        {
          # Attach mutated annotation
          "equals": annotation,
          "comparison": t.Optional[ComparisonInput]
        }
      )

      if self.required == False:
        return t.Optional[TopLevelInput]

      return TopLevelInput

    return annotation


def is_resolver_input_type(obj) -> bool:
  return type(obj).__module__ == "app.util.decorators.resolver" and not isinstance(obj, type)


"""
The resolver decorator does some trick stuff:
  1. Gets all fields off the model flagged as InputField
  2. Generates a dynamic resolver to expose input fields
  3. Generates a dynamic SQL query based off the input from client
  4. Provides SQL and inputs to original resolver to execute
"""
def resolver(input_model, return_type):
  def wrapper(func: t.Callable):
    # Get fields from model
    fields: dict[str, FieldInfo] = input_model.model_fields

    # Get fields that contain the InputSelector class from t.Annotated
    input_fields = {
      f: type for f, type in fields.items()
      if any(isinstance(m, InputField) for m in type.metadata)
    }

    # Define template function to mutate
    def dynamic_func(self, **kwargs):
      stmt = db.select(input_model)

      for field, type in input_fields.items():
        if field in kwargs:
          resolver_input = kwargs[field]
          database_field: FieldInfo = getattr(input_model, field)

          """
          Determine how to handle the resolver input:
            1. If input is a dynamic input class then use the
               `create_stmt_where_clauses` from `InputField`
            2. If input is a list then use the `col.in_` operator
            3. If input is a direct-value then a basic equality operator
          """
          if is_resolver_input_type(resolver_input):
            stmt = InputField.create_stmt_where_clauses(
              stmt=stmt,
              database_field=database_field,
              resolver_input=resolver_input
            )

          elif isinstance(resolver_input, list):
            stmt = stmt.where(db.col(database_field).in_(resolver_input))
          else:
            stmt = stmt.where(database_field == resolver_input)

      return func(self, stmt, **kwargs)

    sig = inspect.signature(dynamic_func)

    # Build new parameters
    parameters = [
      inspect.Parameter(
        name="self", annotation=t.Any, kind=inspect.Parameter.POSITIONAL_OR_KEYWORD
      )
    ]

    # Add parameters for each input field
    for field, type in input_fields.items():
      input_field_metadata = next(
        (m for m in type.metadata if isinstance(m, InputField)),
        None
      )

      annotation = type.annotation

      # Describe a class prefix to stop conflicts
      class_prefix = func.__name__ + "_" + field

      if input_field_metadata:
        annotation = input_field_metadata.annotation(
          class_prefix=class_prefix,
          base_annotation=annotation
        )

      # Attach dynamic GraphQL input to parameters
      parameters.append(
        inspect.Parameter(
          name=field, annotation=annotation, kind=inspect.Parameter.POSITIONAL_OR_KEYWORD
        )
      )

    # Mutate template function signature
    new_sig = sig.replace(
      parameters=parameters,
      return_annotation=return_type or t.Any,
    )

    dynamic_func.__signature__ = new_sig  # type: ignore

    return dynamic_func
  return wrapper

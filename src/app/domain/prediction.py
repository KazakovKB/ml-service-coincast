from dataclasses import dataclass, field
from typing import Sequence, Any, Tuple
from datetime import datetime, UTC


@dataclass
class PredictionJob:
    user_id: int
    model_name: str
    valid_input: Sequence[Any]
    predictions: Sequence[Any]
    invalid_rows: Sequence[Tuple[int, Any]]
    cost: int
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def n_valid(self) -> int:
        return len(self.valid_input)

    def n_invalid(self) -> int:
        return len(self.invalid_rows)

    def summary(self) -> dict:
        return {
            "model": self.model_name,
            "total_rows": self.n_valid() + self.n_invalid(),
            "predicted": self.n_valid(),
            "invalid": self.n_invalid(),
            "cost": self.cost,
            "timestamp": self.created_at.isoformat(),
        }

    def get_invalid_rows_for_user(self) -> list:
        return [row for idx, row in self.invalid_rows]

if __name__ == '__main__':
    from validation import Validator

    # Пользователь загружает данные
    uploaded_data = [
        {"feature1": 1, "feature2": 2},
        {"feature1": None, "feature2": 3},   # невалидная (None)
        {"feature1": 5, "feature2": 1},
        {"feature1": 4, "feature2": 2},
        {"feature1": "rtry", "feature2": 2}, # невалидная (строка вместо числа)
    ]

    # Валидируем входные данные
    validator = Validator()
    validation_result = validator.validate(uploaded_data)

    print("Валидные строки:")
    for row in validation_result.valid_rows:
        print(row)
    print()

    print("Ошибочные строки:")
    for idx, row in validation_result.invalid_rows:
        print(f"Индекс {idx}: {row}")
    print()

    # эмулируем работу ML модели
    predictions = [
        row["feature1"] + row["feature2"]
        for row in validation_result.valid_rows
    ]

    # Формируем PredictionJob
    job = PredictionJob(
        user_id=1,
        model_name="MySimpleModel_v1",
        valid_input=validation_result.valid_rows,
        predictions=predictions,
        invalid_rows=validation_result.invalid_rows,
        cost=len(predictions),
    )

    print("Краткое резюме задачи (summary):")
    print(job.summary(), end="\n\n")

    print("Список невалидных строк (для пользователя):")
    for row in job.get_invalid_rows_for_user():
        print(row)
    print()

    print("Все предсказания по валидным строкам:")
    for input_row, pred in zip(job.valid_input, job.predictions):
        print(f"Входные: {input_row}, Предсказание: {pred}")

    # 6. Использование статистики
    print()
    print(f"Успешных строк: {job.n_valid()}")
    print(f"Ошибочных строк: {job.n_invalid()}")
# 1. Imports
# =====================================
import torch
import torch.nn as nn
import torch.optim as optim
import pennylane as qml
import argparse
import json
from typing import List, Dict

# =====================================
# 2. Quantum Layer Definition
# =====================================
class QuantumLayer(nn.Module):
    """A quantum neural network layer implemented with PennyLane and Torch.

    This layer encodes classical inputs into quantum rotations and applies
    variational layers of parameterized gates. The outputs are expectation
    values of Pauli-Z measurements on each qubit.
    """

    def __init__(self, n_qubits: int, n_layers: int, device_name: str = "lightning.qubit") -> None:
        super().__init__()
        self.n_qubits: int = n_qubits
        self.n_layers: int = n_layers
        self.device_name: str = device_name

        dev = qml.device(self.device_name, wires=self.n_qubits)

        @qml.qnode(dev, interface="torch")
        def circuit(inputs: torch.Tensor, weights: torch.Tensor) -> List[torch.Tensor]:
            # Encode inputs as rotations
            for i in range(self.n_qubits):
                qml.RY(inputs[i], wires=i)

            # Variational layers
            for j in range(self.n_layers):
                for i in range(self.n_qubits):
                    qml.CNOT(wires=[i, (i + 1) % self.n_qubits])
                for i in range(self.n_qubits):
                    qml.RY(weights[j, i], wires=i)

            # Measurements
            return [qml.expval(qml.PauliZ(i)) for i in range(self.n_qubits)]

        weight_shapes: Dict[str, tuple] = {"weights": (self.n_layers, self.n_qubits)}
        self.q_layer: nn.Module = qml.qnn.TorchLayer(circuit, weight_shapes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.dim() == 1:
            x = x.unsqueeze(0)
        outputs: List[torch.Tensor] = [self.q_layer(sample) for sample in x]
        return torch.stack(outputs)

# =====================================
# 3. Hybrid Model Definition
# =====================================
class HybridModel(nn.Module):
    """A hybrid quantum-classical neural network for XOR-like tasks.

    This model first applies a quantum layer to process input data
    and then uses classical fully-connected layers with ReLU activation
    to produce the final 2D output.
    """

    def __init__(self, n_qubits: int, n_layers: int, hidden_size: int) -> None:
        super().__init__()
        self.q_layer: QuantumLayer = QuantumLayer(n_qubits, n_layers)
        self.fc1: nn.Linear = nn.Linear(n_qubits, hidden_size)
        self.relu: nn.ReLU = nn.ReLU()
        self.fc2: nn.Linear = nn.Linear(hidden_size, 2)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        q_out: torch.Tensor = self.q_layer(x)
        hidden: torch.Tensor = self.relu(self.fc1(q_out))
        return self.fc2(hidden)

# =====================================
# 4. Training and Testing Functions
# =====================================
def train_model(model: nn.Module, criterion: nn.Module, optimizer: optim.Optimizer, 
                X: torch.Tensor, y: torch.Tensor, epochs: int, seed: int = 42) -> List[float]:
    # Set random seed for reproducibility
    torch.manual_seed(seed)

    loss_log: List[float] = []
    for epoch in range(epochs):
        optimizer.zero_grad()
        outputs: torch.Tensor = model(X)
        loss: torch.Tensor = criterion(outputs, y)
        loss.backward()
        optimizer.step()
        loss_value: float = loss.item()
        loss_log.append(loss_value)
        print(f"Epoch {epoch+1}/{epochs}, Loss: {loss_value:.4f}")
    print("Training complete.")
    return loss_log

def test_model(model: nn.Module, sample_input: torch.Tensor) -> List[List[float]]:
    prediction: torch.Tensor = model(sample_input)
    print("Sample prediction:", prediction.tolist())
    return prediction.tolist()

# =====================================
# 5. Helper Functions
# =====================================
def run_training(args: argparse.Namespace) -> Dict[str, List]:
    X: torch.Tensor = torch.tensor([[0., 0.], [0., 1.], [1., 0.], [1., 1.]], dtype=torch.float32)
    y: torch.Tensor = torch.tensor([[ 1.,  1.], [ 1., -1.], [-1.,  1.], [-1., -1.]], dtype=torch.float32)

    model: HybridModel = HybridModel(args.n_qubits, args.n_layers, args.hidden_size)
    criterion: nn.Module = nn.MSELoss()
    optimizer: optim.Optimizer = optim.Adam(model.parameters(), lr=args.lr)

    loss_log: List[float] = train_model(model, criterion, optimizer, X, y, args.epochs)
    sample_input: torch.Tensor = torch.tensor([0.5, 0.5])
    prediction: List[List[float]] = test_model(model, sample_input)

    results: Dict[str, List] = {
        "loss_log": loss_log,
        "final_prediction": prediction
    }
    return results

def save_results(results: Dict[str, List], log_file: str) -> None:
    with open(log_file, "w") as f:
        json.dump(results, f, indent=4)
    print(f"Results logged to {log_file}")

# =====================================
# 6. Main Guard
# =====================================
def main() -> None:
    parser = argparse.ArgumentParser(description="Train hybrid quantum-classical model on XOR.")
    parser.add_argument("--n_qubits", type=int, default=2)
    parser.add_argument("--n_layers", type=int, default=2)
    parser.add_argument("--hidden_size", type=int, default=4)
    parser.add_argument("--lr", type=float, default=0.01)
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--log_file", type=str, default="results_log.json")
    args = parser.parse_args()

    results: Dict[str, List] = run_training(args)
    save_results(results, args.log_file)

if __name__ == "__main__":
    main()

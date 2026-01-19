# Training-Grade Industrial Sensor Simulator Design

**Objective**: Transform the OT Data Simulator from a sales demo tool into a high-fidelity training platform for ML model development, anomaly detection, and predictive maintenance.

---

## Executive Summary

### Current State (Sales Demo Quality)
- ✅ Simple sine waves with noise
- ✅ Basic anomaly injection
- ✅ ~379 sensors across 15 industries
- ⚠️ **Limitation**: Patterns too simple for real ML training
- ⚠️ **Limitation**: No realistic interdependencies
- ⚠️ **Limitation**: No physics-based modeling

### Target State (Training Quality)
- 🎯 Physically accurate waveforms
- 🎯 Real-world failure modes
- 🎯 Multi-sensor correlations
- 🎯 Industrial-grade complexity
- 🎯 Validated against real equipment data
- 🎯 Suitable for ML model training

---

## Table of Contents

1. [Gap Analysis](#gap-analysis)
2. [Physics-Based Modeling](#physics-based-modeling)
3. [Realistic Failure Modes](#realistic-failure-modes)
4. [Multi-Sensor Correlations](#multi-sensor-correlations)
5. [Data Validation](#data-validation)
6. [Implementation Roadmap](#implementation-roadmap)
7. [ML Training Use Cases](#ml-training-use-cases)

---

## Gap Analysis

### What Makes Current Simulator "Demo Quality"

| Aspect | Current (Demo) | Training-Grade Requirement |
|--------|----------------|---------------------------|
| **Waveforms** | Simple sine + Gaussian noise | Physics-based with harmonics, resonances |
| **Correlations** | Independent sensors | Cross-sensor dependencies (thermal, mechanical) |
| **Failure Modes** | Random spikes/freezes | Realistic degradation patterns (bearing wear, fouling) |
| **Temporal Dynamics** | Instant state changes | Gradual transitions with inertia |
| **Operating Modes** | Single steady state | Startup, shutdown, load changes, maintenance |
| **Seasonal Effects** | None | Temperature, humidity, production schedules |
| **Validation** | Subjective "looks good" | Validated against real equipment data |

### Key Limitations for ML Training

1. **Too Predictable**: ML models overfit to simple patterns
2. **No Hidden States**: Real equipment has internal degradation not visible in single sensor
3. **Unrealistic Anomalies**: Random spikes don't mimic real failures
4. **Missing Context**: No production schedules, maintenance events, external conditions
5. **Insufficient Diversity**: Not enough variety in normal vs abnormal patterns

---

## Physics-Based Modeling

### Approach 1: First-Principles Models

**For each sensor type, implement physics equations:**

#### Example: Vibration Sensor (Crusher Motor)

**Current (Demo)**:
```python
value = base + amplitude * sin(2π * frequency * t) + noise
```

**Training-Grade (Physics-Based)**:
```python
# Bearing defect frequencies (BPFO, BPFI, BSF, FTF)
class BearingVibration:
    def __init__(self):
        self.shaft_speed = 1800  # RPM
        self.bearing = SKF_6309  # Bearing spec
        self.bpfo_frequency = self.calc_bpfo()  # Ball pass outer race
        self.bpfi_frequency = self.calc_bpfi()  # Ball pass inner race
        self.bsf_frequency = self.calc_bsf()    # Ball spin frequency
        self.ftf_frequency = self.calc_ftf()    # Cage frequency

        # Health degradation state (0=new, 1=failed)
        self.bearing_health = 0.0
        self.misalignment = 0.0
        self.imbalance = 0.0

    def generate(self, t):
        # Fundamental shaft frequency
        shaft_hz = self.shaft_speed / 60
        base = 2.0 * np.sin(2 * np.pi * shaft_hz * t)

        # Harmonics (2x, 3x shaft speed)
        harmonics = sum([
            0.5 * np.sin(2 * np.pi * n * shaft_hz * t)
            for n in [2, 3, 4]
        ])

        # Bearing defect frequencies (amplitude grows with degradation)
        defects = 0
        if self.bearing_health > 0.3:
            defects += self.bearing_health * 5.0 * np.sin(2 * np.pi * self.bpfo_frequency * t)
        if self.bearing_health > 0.5:
            defects += self.bearing_health * 3.0 * np.sin(2 * np.pi * self.bpfi_frequency * t)

        # Misalignment (1x shaft with sidebands)
        if self.misalignment > 0:
            defects += self.misalignment * 3.0 * (
                np.sin(2 * np.pi * shaft_hz * t) *
                (1 + 0.5 * np.sin(2 * np.pi * 2 * t))  # Modulation
            )

        # Imbalance (1x shaft, radial)
        if self.imbalance > 0:
            defects += self.imbalance * 4.0 * np.sin(2 * np.pi * shaft_hz * t)

        # Broadband noise (increases with age)
        noise = np.random.normal(0, 0.1 + 0.5 * self.bearing_health)

        return base + harmonics + defects + noise
```

**Why This Matters**:
- ML models learn real bearing fault signatures
- Can detect early degradation (bearing_health < 0.3)
- Distinguishes between fault types (bearing, misalignment, imbalance)
- Validated against ISO 10816 vibration standards

#### Example: Temperature Sensor (Transformer Oil)

**Current (Demo)**:
```python
temp = 65 + 5 * sin(t) + noise  # Simple
```

**Training-Grade (Thermal Dynamics)**:
```python
class TransformerThermalModel:
    def __init__(self):
        self.thermal_mass = 5000  # kg oil
        self.heat_capacity = 2.0   # kJ/kg·K
        self.cooling_coefficient = 0.02
        self.ambient_temp = 25
        self.load_power = 0  # MW
        self.oil_temp = 55  # Current temperature

        # Degradation states
        self.cooling_efficiency = 1.0  # 1.0 = new, 0.5 = fouled
        self.winding_hotspot_factor = 1.0  # 1.0 = normal, 1.5 = degraded insulation

    def step(self, dt, load_power):
        # Heat generation from load
        losses = (load_power ** 2) * 0.01  # I²R losses
        heat_in = losses * self.winding_hotspot_factor

        # Heat dissipation (Newton's law of cooling)
        heat_out = (
            self.cooling_coefficient *
            self.cooling_efficiency *
            (self.oil_temp - self.ambient_temp)
        )

        # Temperature change (thermal inertia)
        dtemp_dt = (heat_in - heat_out) / (self.thermal_mass * self.heat_capacity)
        self.oil_temp += dtemp_dt * dt

        # Add sensor noise
        measured = self.oil_temp + np.random.normal(0, 0.2)

        return measured
```

**Why This Matters**:
- Realistic thermal time constants (minutes to hours)
- Load-dependent heating (matches real transformers)
- Cooling system degradation (fouling) causes gradual temp rise
- Can train models to predict overheating from load profiles

### Approach 2: Data-Driven Models (Transfer Learning)

**Use real equipment data to train generative models:**

```python
from sklearn.mixture import GaussianMixture
import numpy as np

class DataDrivenSensor:
    """Learn patterns from real sensor data."""

    def __init__(self, real_data_file):
        # Load real equipment data
        real_data = pd.read_csv(real_data_file)

        # Train Gaussian Mixture Model on normal operation
        self.gmm_normal = GaussianMixture(n_components=5).fit(
            real_data[real_data['label'] == 'normal']
        )

        # Train GMM on fault conditions
        self.gmm_fault = GaussianMixture(n_components=3).fit(
            real_data[real_data['label'] == 'fault']
        )

        # Learn temporal autocorrelation
        self.ar_model = AutoReg(real_data['value'], lags=20).fit()

    def generate(self, mode='normal', duration=3600):
        """Generate realistic time series."""
        if mode == 'normal':
            # Sample from learned normal distribution
            samples, _ = self.gmm_normal.sample(duration)
        else:
            # Sample from fault distribution
            samples, _ = self.gmm_fault.sample(duration)

        # Apply temporal smoothing (AR model)
        smoothed = self.ar_model.predict(start=0, end=duration-1)

        return smoothed + samples.flatten()
```

**Data Sources** (can partner with customers for anonymized data):
- Rockwell Automation: FactoryTalk historian data
- Siemens: MindSphere equipment data
- OEM equipment logs (anonymized)
- Publicly available datasets (NASA bearing, CWRU, etc.)

---

## Realistic Failure Modes

### Common Industrial Failure Patterns

| Failure Mode | Signature | Time to Failure | Affected Sensors |
|--------------|-----------|-----------------|------------------|
| **Bearing Wear** | Increasing vibration at bearing frequencies | 6-12 months | Vibration, temperature |
| **Cavitation (Pump)** | High-frequency noise bursts | 3-6 months | Vibration, flow, pressure |
| **Fouling (Heat Exchanger)** | Gradual temperature rise, pressure drop | 6-18 months | Temperature, pressure, flow |
| **Insulation Degradation** | Increasing partial discharge | 12-24 months | Voltage, current, temperature |
| **Belt Slippage** | Speed variation, higher temperature | Days-weeks | Speed, vibration, current |
| **Seal Leakage** | Pressure drop, flow increase | 3-12 months | Pressure, flow, level |

### Implementation: Degradation State Machines

```python
class EquipmentDegradation:
    """Models realistic failure progression."""

    def __init__(self, equipment_type):
        self.health = 1.0  # 1.0 = new, 0.0 = failed
        self.degradation_rate = self.get_failure_rate(equipment_type)
        self.failure_modes = self.get_failure_modes(equipment_type)
        self.operating_hours = 0
        self.stress_factors = {
            'temperature': 1.0,  # High temp accelerates degradation
            'load': 1.0,         # Overload accelerates degradation
            'contamination': 1.0 # Dirt/moisture accelerates degradation
        }

    def update(self, dt, operating_conditions):
        """Update health state based on operating conditions."""
        self.operating_hours += dt / 3600

        # Accelerated degradation under stress
        stress_multiplier = np.prod(list(self.stress_factors.values()))

        # Degradation follows Weibull distribution (realistic failure curve)
        from scipy.stats import weibull_min
        failure_prob = weibull_min.cdf(
            self.operating_hours,
            c=2.0,  # Shape parameter (wear-out failures)
            scale=8760 * 3  # Scale (3 years MTBF)
        )

        self.health = 1.0 - failure_prob * stress_multiplier

        # Activate failure modes as health degrades
        active_failures = []
        if self.health < 0.7:
            active_failures.append('early_wear')
        if self.health < 0.5:
            active_failures.append('moderate_degradation')
        if self.health < 0.3:
            active_failures.append('severe_degradation')
        if self.health < 0.1:
            active_failures.append('imminent_failure')

        return active_failures
```

---

## Multi-Sensor Correlations

### Real-World Interdependencies

**Example: Crusher System (Mining)**

```python
class CrusherSystem:
    """Physically coupled sensors."""

    def __init__(self):
        self.motor_speed = 1200  # RPM
        self.motor_current = 0
        self.motor_torque = 0
        self.motor_temp = 40
        self.bearing_temp = 35
        self.vibration_x = 0
        self.vibration_y = 0
        self.throughput = 0  # tons/hour

        # Physical parameters
        self.motor_inertia = 50  # kg·m²
        self.bearing_health = 1.0
        self.load_variability = 0.1

    def update(self, dt, feed_rate):
        """All sensors update together with physics."""

        # Crushing load (varies with material hardness)
        crushing_load = feed_rate * (1 + self.load_variability * np.random.randn())

        # Motor dynamics (torque = load + friction)
        required_torque = crushing_load + (1 - self.bearing_health) * 50
        self.motor_torque = required_torque

        # Current proportional to torque (P = T × ω)
        self.motor_current = self.motor_torque * self.motor_speed / 1000

        # Temperature rises with load (thermal inertia)
        heat_generation = self.motor_current ** 2 * 0.01
        heat_dissipation = 0.02 * (self.motor_temp - 25)
        self.motor_temp += (heat_generation - heat_dissipation) * dt / 60

        # Bearing temperature correlates with motor temp + friction
        bearing_friction = (1 - self.bearing_health) * 10
        self.bearing_temp = self.motor_temp * 0.8 + bearing_friction

        # Vibration increases with bearing wear and load variation
        self.vibration_x = (
            1.0 +
            (1 - self.bearing_health) * 5 +
            crushing_load * 0.1 * np.sin(2 * np.pi * self.motor_speed / 60 * t)
        )

        # Throughput depends on speed and jamming probability
        jam_probability = max(0, crushing_load - 100) / 100
        if np.random.random() < jam_probability * dt:
            self.throughput = 0  # Jammed!
            self.motor_current *= 2  # Current spike
        else:
            self.throughput = feed_rate * 0.9

        return {
            'motor_speed': self.motor_speed,
            'motor_current': self.motor_current,
            'motor_temp': self.motor_temp,
            'bearing_temp': self.bearing_temp,
            'vibration_x': self.vibration_x,
            'throughput': self.throughput
        }
```

**Why This Matters**:
- ML models learn cross-sensor patterns
- Can detect anomalies that only show up in correlations
- Example: High current + low throughput = jam condition
- Example: High vibration + high bearing temp = imminent failure

---

## Data Validation

### How to Validate Simulator Against Real Equipment

1. **Statistical Validation**:
```python
from scipy.stats import ks_2samp, anderson_ksamp

def validate_distribution(simulated, real):
    """Compare distributions using Kolmogorov-Smirnov test."""
    statistic, pvalue = ks_2samp(simulated, real)

    if pvalue < 0.05:
        print(f"❌ Distributions differ significantly (p={pvalue:.4f})")
        return False
    else:
        print(f"✅ Distributions match (p={pvalue:.4f})")
        return True
```

2. **Frequency Domain Validation**:
```python
def validate_frequency_spectrum(simulated, real, sample_rate):
    """Compare FFT spectra."""
    from scipy.fft import fft, fftfreq

    # Compute FFTs
    sim_fft = np.abs(fft(simulated))
    real_fft = np.abs(fft(real))
    freqs = fftfreq(len(simulated), 1/sample_rate)

    # Compare peak frequencies
    sim_peaks = find_peaks(sim_fft, height=threshold)
    real_peaks = find_peaks(real_fft, height=threshold)

    peak_match = compare_peaks(sim_peaks, real_peaks, tolerance=0.1)
    return peak_match
```

3. **Anomaly Detection Validation**:
```python
def validate_anomaly_detection(simulated, real):
    """Train ML model on both, compare performance."""
    from sklearn.ensemble import IsolationForest

    # Train on simulated data
    model_sim = IsolationForest().fit(simulated)
    f1_sim = evaluate(model_sim, real_test_data)

    # Train on real data
    model_real = IsolationForest().fit(real)
    f1_real = evaluate(model_real, real_test_data)

    # Simulator is good if F1 scores within 10%
    return abs(f1_sim - f1_real) / f1_real < 0.10
```

---

## Implementation Roadmap

### Phase 1: Physics-Based Models (4-6 weeks)

**Week 1-2: Vibration Sensors**
- [ ] Implement bearing defect frequency calculations
- [ ] Add shaft harmonics
- [ ] Model misalignment and imbalance
- [ ] Validate against NASA bearing dataset

**Week 3-4: Thermal Sensors**
- [ ] Implement thermal mass and heat transfer
- [ ] Add cooling system models
- [ ] Model load-dependent heating
- [ ] Validate against transformer manufacturer data

**Week 5-6: Flow and Pressure**
- [ ] Implement Bernoulli's equation
- [ ] Add pump curves
- [ ] Model cavitation
- [ ] Validate against pump test data

### Phase 2: Failure Modes (2-3 weeks)

**Week 1: Degradation State Machines**
- [ ] Implement Weibull-based health degradation
- [ ] Add stress factors (temp, load, contamination)
- [ ] Create failure progression timelines

**Week 2: Fault Signatures**
- [ ] Bearing wear signatures
- [ ] Fouling signatures
- [ ] Electrical fault signatures

**Week 3: Validation**
- [ ] Compare against real failure data
- [ ] Tune parameters for realism

### Phase 3: Multi-Sensor Correlations (2-3 weeks)

**Week 1: Equipment Systems**
- [ ] Create coupled sensor models
- [ ] Implement physical constraints
- [ ] Add feedback loops

**Week 2: Operating Modes**
- [ ] Startup/shutdown sequences
- [ ] Load changes
- [ ] Maintenance mode

**Week 3: External Factors**
- [ ] Seasonal effects
- [ ] Production schedules
- [ ] Environmental conditions

### Phase 4: Data-Driven Augmentation (2-3 weeks)

**Week 1: Data Collection**
- [ ] Partner with customers for real data
- [ ] Anonymize and clean data
- [ ] Create datasets for each industry

**Week 2: Model Training**
- [ ] Train GMMs on normal operation
- [ ] Train GMMs on fault conditions
- [ ] Extract temporal patterns (AR models)

**Week 3: Integration**
- [ ] Blend physics and data-driven models
- [ ] Validate combined approach
- [ ] Tune for realism

### Phase 5: ML Training Validation (2 weeks)

**Week 1: ML Model Training**
- [ ] Train anomaly detection models
- [ ] Train predictive maintenance models
- [ ] Compare performance: simulator vs real data

**Week 2: Production Readiness**
- [ ] Documentation
- [ ] API for ML training pipelines
- [ ] Databricks integration (MLflow, Feature Store)

---

## ML Training Use Cases

### Use Case 1: Anomaly Detection

**Objective**: Train ML models to detect equipment anomalies

**Requirements**:
- 10,000+ hours of normal operation data
- 100+ examples of each anomaly type
- Realistic false positive rate (<5%)

**Simulator Deliverables**:
```python
# Generate training dataset
dataset = simulator.generate_training_data(
    duration_hours=10000,
    anomaly_types=['bearing_wear', 'cavitation', 'fouling'],
    anomaly_frequency=0.05,  # 5% of time
    save_to='databricks://main.training.anomaly_detection_v1'
)
```

### Use Case 2: Predictive Maintenance

**Objective**: Predict time-to-failure

**Requirements**:
- Full failure progressions (healthy → failed)
- Realistic RUL (Remaining Useful Life) curves
- Multiple failure modes per asset type

**Simulator Deliverables**:
```python
# Generate RUL training data
rul_dataset = simulator.generate_rul_data(
    equipment_types=['motor', 'pump', 'bearing'],
    failures_per_type=50,
    include_censored_data=True,  # Not all run to failure
    save_to='databricks://main.training.predictive_maintenance_v1'
)
```

### Use Case 3: Process Optimization

**Objective**: Optimize operating parameters

**Requirements**:
- Multi-sensor correlations
- Operating envelope boundaries
- Cost functions (energy, throughput, wear)

**Simulator Deliverables**:
```python
# Generate process optimization data
opt_dataset = simulator.generate_optimization_data(
    parameter_space={
        'crusher_speed': (800, 1500),  # RPM
        'feed_rate': (50, 150),         # tons/hour
    },
    objectives=['throughput', 'energy_efficiency', 'wear_rate'],
    samples=10000,
    save_to='databricks://main.training.process_optimization_v1'
)
```

---

## Validation Metrics

### Simulator Quality Scorecard

| Metric | Target | Current | Gap |
|--------|--------|---------|-----|
| **Statistical Match** (KS test p-value) | > 0.05 | N/A | TBD |
| **Frequency Match** (peak correlation) | > 0.90 | N/A | TBD |
| **Anomaly F1 Score** (sim vs real trained) | > 0.85 | N/A | TBD |
| **Failure Progression Realism** (SME review) | 4.0/5.0 | N/A | TBD |
| **Cross-Sensor Correlation** (Pearson r) | > 0.80 | N/A | TBD |

---

## Cost and Resources

### Development Effort

| Phase | Duration | Team Size | Cost Estimate |
|-------|----------|-----------|---------------|
| Physics Models | 6 weeks | 2 engineers | $60K |
| Failure Modes | 3 weeks | 2 engineers | $30K |
| Correlations | 3 weeks | 2 engineers | $30K |
| Data-Driven | 3 weeks | 1 ML engineer + 1 engineer | $40K |
| Validation | 2 weeks | 1 senior engineer | $20K |
| **Total** | **17 weeks** | **~2 FTEs** | **$180K** |

### Data Acquisition

- Partner with 2-3 customers for anonymized data: $50K-100K
- Purchase public datasets (NASA, CWRU, etc.): $5K-10K
- OEM collaboration (Rockwell, Siemens): Potentially free (partnership)

---

## Success Criteria

### Training-Grade Certification

A simulator is "training-grade" if:

1. ✅ ML models trained on simulated data achieve **>85% F1 score** on real data
2. ✅ SMEs (Subject Matter Experts) rate realism **>4.0/5.0**
3. ✅ Statistical tests (KS, Anderson-Darling) show **p > 0.05** (distributions match)
4. ✅ Frequency spectra match real equipment **>90% peak correlation**
5. ✅ Failure progressions validated by **3+ OEMs or end users**

---

## Conclusion

Transforming the simulator from sales demo to training-grade requires:

1. **Physics-Based Modeling**: Replace sine waves with differential equations
2. **Realistic Failure Modes**: Implement Weibull degradation and fault signatures
3. **Multi-Sensor Correlations**: Model physical coupling between sensors
4. **Data Validation**: Validate against real equipment using statistical tests
5. **ML Training Validation**: Prove models trained on sim data work on real data

**Timeline**: 17 weeks (~4 months)
**Investment**: ~$180K development + $50K-100K data acquisition
**ROI**: Enable customers to train production ML models before deploying expensive IIoT infrastructure

**Next Steps**:
1. Prioritize industries (start with Mining + Utilities)
2. Partner with 2-3 customers for data
3. Begin Phase 1 (Physics Models) for top 20 sensor types
4. Validate MVP with one customer pilot

---

**Status**: 📋 Design Complete - Ready for Implementation
**Owner**: TBD
**Stakeholders**: Sales Engineering, Field Engineers, ML/AI Team, Customer Success

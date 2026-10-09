# sim_app.py
import streamlit as st
import simpy
import pandas as pd
import matplotlib.pyplot as plt
import random # For random number generation in simulation

# --- Streamlit Page Configuration ---
st.set_page_config(
    page_title="Simple DES App",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("Simple Discrete Event Simulation Builder")
st.markdown("Build your process flow by adding and configuring blocks, then run the simulation!")

# --- Session State Initialization ---
if 'blocks' not in st.session_state:
    st.session_state.blocks = []
if 'simulation_results' not in st.session_state:
    st.session_state.simulation_results = None
# sim_app.py
import streamlit as st
import simpy
import pandas as pd
import matplotlib.pyplot as plt
import random # For random number generation in simulation

# --- Streamlit Page Configuration ---
st.set_page_config(
    page_title="Simple DES App",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("Simple Discrete Event Simulation Builder")
st.markdown("Build your process flow by adding and configuring blocks, then run the simulation!")

# --- Session State Initialization ---
if 'blocks' not in st.session_state:
    st.session_state.blocks = []
if 'simulation_results' not in st.session_state:
    st.session_state.simulation_results = None

# --- SimPy Simulation Logic ---

class Entity:
    def __init__(self, name, arrival_time):
        self.name = name
        self.arrival_time = arrival_time
        self.start_service_time = None
        self.end_service_time = None
        self.exit_time = None
        self.wait_time = 0

def source(env, name, inter_arrival_time, next_process_func):
    """Generates entities with a given inter-arrival time."""
    entity_count = 0
    while True:
        yield env.timeout(random.expovariate(1.0 / inter_arrival_time))
        entity_count += 1
        entity = Entity(f"Entity_{entity_count}", env.now)
        st.session_state.log.append(f"{env.now:.2f}: {entity.name} arrived.")
        env.process(next_process_func(env, entity))

def server(env, entity, resource, service_time, results_collector):
    """Processes an entity using a SimPy resource."""
    with resource.request() as req:
        yield req
        entity.start_service_time = env.now
        entity.wait_time += (entity.start_service_time - entity.arrival_time) # Accumulate wait time
        st.session_state.log.append(f"{env.now:.2f}: {entity.name} started service at {resource.name}.")
        yield env.timeout(random.expovariate(1.0 / service_time))
        entity.end_service_time = env.now
        st.session_state.log.append(f"{env.now:.2f}: {entity.name} finished service at {resource.name}.")
        results_collector.append(entity) # Collect entity for results
        # If there's a next process, pass the entity to it. For this simple linear flow, we'll just collect.

def run_simulation(blocks_config, sim_duration):
    """Constructs and runs the SimPy simulation based on user-defined blocks."""
    st.session_state.log = [] # Clear log for new run
    env = simpy.Environment()
    
    # Store SimPy resources and processes
    simpy_resources = {}
    
    # Collect all entities that pass through the system
    all_entities = []

    # Create SimPy resources based on configured blocks
    for i, block in enumerate(blocks_config):
        if block['type'] == 'Server':
            resource_name = f"Server_{i}"
            simpy_resources[resource_name] = simpy.Resource(env, capacity=block['capacity'])
            block['simpy_resource_name'] = resource_name # Store resource name for later use

    # Now, link the processes
    # For this simple example, we assume a linear flow: Source -> Server1 -> Server2 -> ... -> Sink
    
    # The 'sink' will just be the collection of entities in all_entities
    
    # Find the first block (Source) and set up its next process
    source_block_config = None
    for block in blocks_config:
        if block['type'] == 'Source':
            source_block_config = block
            break
    
    if not source_block_config:
        st.error("A 'Source' block is required to start the simulation.")
        return None, None

    # This is a simplified way to chain processes.
    # In a more complex app, you'd build a graph and traverse it.
    
    # Define a function that represents the entire flow for an entity
    def entity_flow(env, entity):
        current_block_index = 0
        
        while current_block_index < len(blocks_config):
            block = blocks_config[current_block_index]
            
            if block['type'] == 'Source':
                # Source just generates, it doesn't process an incoming entity
                pass 
            elif block['type'] == 'Server':
                resource = simpy_resources[block['simpy_resource_name']]
                with resource.request() as req:
                    yield req
                    entity.start_service_time = env.now
                    entity.wait_time += (entity.start_service_time - entity.arrival_time)
                    st.session_state.log.append(f"{env.now:.2f}: {entity.name} started service at {resource.name}.")
                    yield env.timeout(random.expovariate(1.0 / block['service_time']))
                    entity.end_service_time = env.now
                    st.session_state.log.append(f"{env.now:.2f}: {entity.name} finished service at {resource.name}.")
            elif block['type'] == 'Sink':
                # Sink just marks the end of the flow for an entity
                entity.exit_time = env.now
                st.session_state.log.append(f"{env.now:.2f}: {entity.name} exited the system.")
                all_entities.append(entity)
                break # Entity has reached the sink, stop processing its flow
            
            current_block_index += 1
        
        # If an entity finishes all blocks but doesn't hit a Sink, mark its exit
        if entity.exit_time is None:
            entity.exit_time = env.now
            all_entities.append(entity)


    # Start the source process
    def start_source(env, inter_arrival_time):
        entity_count = 0
        while True:
            yield env.timeout(random.expovariate(1.0 / inter_arrival_time))
            entity_count += 1
            entity = Entity(f"Entity_{entity_count}", env.now)
            st.session_state.log.append(f"{env.now:.2f}: {entity.name} arrived.")
            env.process(entity_flow(env, entity))

    env.process(start_source(env, source_block_config['inter_arrival_time']))

    # Run the simulation
    env.run(until=sim_duration)

    return all_entities, st.session_state.log


# --- UI for Building Process Flow ---

st.sidebar.header("Simulation Settings")
sim_duration = st.sidebar.number_input("Simulation Duration (time units)", min_value=10, value=100, step=10)

st.sidebar.header("Build Your Process Flow")

# Button to add a new block
if st.sidebar.button("Add New Block"):
    st.session_state.blocks.append({'type': 'Source', 'inter_arrival_time': 5, 'service_time': 3, 'capacity': 1})

# Initialize has_source and has_sink before they are potentially used
has_source = False
has_sink = False

# Display and configure existing blocks
if st.session_state.blocks:
    st.subheader("Your Process Flow")
    
    # Use a placeholder for reordering logic
    # new_blocks_order = [] # This line is not strictly needed for the current reordering logic
    
    for i, block in enumerate(st.session_state.blocks):
        with st.expander(f"Block {i+1}: {block['type']}", expanded=True):
            col1, col2, col3 = st.columns([3, 1, 1])
            
            # Block Type Selection
            block_type = col1.selectbox(
                f"Type for Block {i+1}",
                ['Source', 'Server', 'Sink'],
                index=['Source', 'Server', 'Sink'].index(block['type']),
                key=f"block_type_{i}"
            )
            st.session_state.blocks[i]['type'] = block_type

            # Parameters based on block type
            if block_type == 'Source':
                inter_arrival_time = st.number_input(
                    f"Inter-arrival Time (mean) for Block {i+1}",
                    min_value=0.1, value=block.get('inter_arrival_time', 5.0), step=0.1, format="%.1f",
                    key=f"source_iat_{i}"
                )
                st.session_state.blocks[i]['inter_arrival_time'] = inter_arrival_time
            elif block_type == 'Server':
                service_time = st.number_input(
                    f"Service Time (mean) for Block {i+1}",
                    min_value=0.1, value=block.get('service_time', 3.0), step=0.1, format="%.1f",
                    key=f"server_st_{i}"
                )
                capacity = st.number_input(
                    f"Capacity for Block {i+1}",
                    min_value=1, value=block.get('capacity', 1), step=1,
                    key=f"server_cap_{i}"
                )
                st.session_state.blocks[i]['service_time'] = service_time
                st.session_state.blocks[i]['capacity'] = capacity
            # Sink has no specific parameters for this simple example

            # Reorder and Delete Buttons
            with col2:
                if st.button("⬆️ Move Up", key=f"move_up_{i}"):
                    if i > 0:
                        st.session_state.blocks[i], st.session_state.blocks[i-1] = st.session_state.blocks[i-1], st.session_state.blocks[i]
                        st.experimental_rerun()
            with col3:
                if st.button("⬇️ Move Down", key=f"move_down_{i}"):
                    if i < len(st.session_state.blocks) - 1:
                        st.session_state.blocks[i], st.session_state.blocks[i+1] = st.session_state.blocks[i+1], st.session_state.blocks[i]
                        st.experimental_rerun()
            if st.button("❌ Delete Block", key=f"delete_{i}"):
                del st.session_state.blocks[i]
                st.experimental_rerun()
    
    # These lines are now correctly placed to update the variables if blocks exist
    has_source = any(b['type'] == 'Source' for b in st.session_state.blocks)
    has_sink = any(b['type'] == 'Sink' for b in st.session_state.blocks)

    if not has_source:
        st.warning("Please add at least one 'Source' block to generate entities.")
    if not has_sink:
        st.warning("Please add at least one 'Sink' block to collect results.")

else:
    st.info("Add your first block using the 'Add New Block' button in the sidebar!")


# --- Run Simulation Button ---
st.sidebar.markdown("---")
if st.sidebar.button("Run Simulation", disabled=not (has_source and has_sink)):
    with st.spinner("Running simulation..."):
        entities, sim_log = run_simulation(st.session_state.blocks, sim_duration)
        st.session_state.simulation_results = {
            'entities': entities,
            'log': sim_log
        }
    st.success("Simulation complete!")
    st.experimental_rerun() # Rerun to display results section

# --- Display Results ---
if st.session_state.simulation_results:
    st.subheader("Simulation Results")
    
    entities = st.session_state.simulation_results['entities']
    sim_log = st.session_state.simulation_results['log']

    if entities:
        df_results = pd.DataFrame([{
            'Entity': e.name,
            'Arrival Time': e.arrival_time,
            'Start Service Time': e.start_service_time,
            'End Service Time': e.end_service_time,
            'Exit Time': e.exit_time,
            'Total Wait Time': e.wait_time,
            'Total System Time': e.exit_time - e.arrival_time if e.exit_time is not None else None
        } for e in entities])

        st.dataframe(df_results)

        st.markdown("---")
        st.subheader("Key Metrics")
        
        total_entities = len(entities)
        avg_wait_time = df_results['Total Wait Time'].mean() if not df_results['Total Wait Time'].isnull().all() else 0
        avg_system_time = df_results['Total System Time'].mean() if not df_results['Total System Time'].isnull().all() else 0
        
        st.write(f"**Total Entities Processed:** {total_entities}")
        st.write(f"**Average Wait Time:** {avg_wait_time:.2f} time units")
        st.write(f"**Average System Time:** {avg_system_time:.2f} time units")

        st.markdown("---")
        st.subheader("Wait Time Distribution")
        fig, ax = plt.subplots()
        ax.hist(df_results['Total Wait Time'].dropna(), bins=20, edgecolor='black')
        ax.set_title("Distribution of Total Wait Times")
        ax.set_xlabel("Wait Time")
        ax.set_ylabel("Frequency")
        st.pyplot(fig)

        st.markdown("---")
        st.subheader("Simulation Log")
        st.text_area("Raw Simulation Events", "\n".join(sim_log), height=300)

    else:
        st.warning("No entities were processed during the simulation. Check your source and duration settings.")

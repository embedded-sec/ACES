

## Creating New Compartmentalization Policies

1.  Define a function that takes the PDG graph(G),
    and compartment description tree (T)

```
def my_compart_policy(G,T):
    ....
```

2.  Register Your policy:  This is done by adding it to Partition Methods dict
    in the main if (i.e.,  if __name__ =="__main__":)

```
PARTITION_METHODS = {"filename":partition_by_filename,
                       'peripheral':partition_by_peripheral,
                     "my_policy":my_compart_policy}
```

3. Build using your Policy

```
make all HEXBOX_METHOD=my_policy
```



### Tips on Creating Compartments

G is  the PDG, each node is a function name. You should copying it so the PDG is
preserved.  Peripherals have already been mapped to the peripheral nodes, using the
device tree. (i.e., Start and top attributes are known)

```
R = G.copy()
```

Each node has many attributes:

*  'Type': Options: Fuction, Global, Peripheral
*  'LLVM_Type' : This is the type of object llvm treats this as (eg. int*, function prototype, etc)


Example Function Node

```
name = u'HAL_RCC_ClockConfig'
attrs = {u'Address Taken': False,
 u'LLVM_Type': u'i8 (%struct.RCC_ClkInitTypeDef*, i32)*',
 u'Type': u'Function',
 u'Filename': u'../../../Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_rcc.c'
```

Example Global Node
```
name = u'GPIO_PIN'
attrs =  {'color': 'magenta',
          'shape': 'box',
          u'Filename': u'../../../Drivers/BSP/STM32F4-Discovery/stm32f4_discovery.c',
          u'Type': u'Global',
          u'Size': 4}
```
Example Peripheral Node

```
name = '.periph.RCC'
attrs =  {'Name_KEY': 'RCC',
          'Type': 'Peripheral',
          'Base_Addr': 1073887232,
          'End_Addr': 1073888255}
```

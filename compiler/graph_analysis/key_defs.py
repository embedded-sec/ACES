PERIPHERAL_KEY = "Peripherals"
INCLUDE_KEY = "Include"
BASE_ADDR_KEY = "Base_Addr"
END_ADDR_KEY = "End_Addr"
NAME_KEY = 'Name_KEY'
HEXBOX_TEXT_BASE_NAME = '.hexbox_text_'
HEXBOX_DATA_BASE_NAME = '.hexbox_var_'
HEXBOX_PERIPHERAL_BASE_NAME = '.periph_region_'
REGION_KEY = 'region'
REGION_NAME = 'region_name'
FUNCTION_TYPE = 'Function'
FILENAME_TYPE = "Filename"
GLOBAL_TYPE = "Global"
TYPE_KEY = 'Type'
PERIPHERAL_NODE_TYPE = 'Peripheral'
PERIPHERAL_EDGE_TYPE = PERIPHERAL_NODE_TYPE
ALIAS_EDGE_TYPE = 'Alias'
DATA_EDGE_TYPE = 'Data'
OBJECTS_KEY = "R_OBJECTS"

CODE_REGION_KEY = ".CODE_REGION_"
DATA_REGION_KEY = ".DATA_REGION_"
PERIPHERAL_REGION_KEY = ".PERIPH_REGION"
SIZE_KEY = "SIZE"
PWR2_SIZE_KEY = "PWR2"
#MPU_REGION_KEY = ".MPU_REGION"
ATTR_KEY = "ATTR_KEY"
MERGE_KEY = "MERGE_KEY"

KEY_MPU_TREE_NAME = "MPU_TREE_NAME"
KEY_REQUIRED_PERIPHERALS = "REQUIRED_PERIPHS"

PRIV_KEY = "Priv"

# Policy Keys
POLICY_KEY_REGIONS = "Regions"
POLICY_KEY_MPU_CONFIG = "MPU_CONFIG"
POLICY_KEY_COMPARTMENTS = "Compartments"
POLICY_REGION_KEY_OBJECTS = "Objects"
POLICY_REGION_KEY_TYPE = "Type"
POLICY_NUM_MPU_REGIONS = "NUM_MPU_REGIONS"

IRQ_REGION_NAME = ".IRQ_CODE_REGION"
INTERRUPT_HANDLERS =[ "SysTick_Handler",
"Reset_Handler",
"NMI_Handler",
"HardFault_Handler",
"MemManage_Handler",
"BusFault_Handler",
"UsageFault_Handler",
"SVC_Handler",
"DebugMon_Handler",
"PendSV_Handler",
"SysTick_Handler",
"WWDG_IRQHandler",
"PVD_IRQHandler",
"TAMP_STAMP_IRQHandler",
"RTC_WKUP_IRQHandler",
"FLASH_IRQHandler",
"RCC_IRQHandler",
"EXTI0_IRQHandler",
"EXTI1_IRQHandler",
"EXTI2_IRQHandler",
"EXTI3_IRQHandler",
"EXTI4_IRQHandler",
"DMA1_Stream0_IRQHandler",
"DMA1_Stream1_IRQHandler",
"DMA1_Stream2_IRQHandler",
"DMA1_Stream3_IRQHandler",
"DMA1_Stream4_IRQHandler",
"DMA1_Stream5_IRQHandler",
"DMA1_Stream6_IRQHandler",
"ADC_IRQHandler",
"CAN1_TX_IRQHandler",
"CAN1_RX0_IRQHandler",
"CAN1_RX1_IRQHandler",
"CAN1_SCE_IRQHandler",
"EXTI9_5_IRQHandler",
"TIM1_BRK_TIM9_IRQHandler",
"TIM1_UP_TIM10_IRQHandler",
"TIM1_TRG_COM_TIM11_IRQHandler",
"TIM1_CC_IRQHandler",
"TIM2_IRQHandler",
"TIM3_IRQHandler",
"TIM4_IRQHandler",
"I2C1_EV_IRQHandler",
"I2C1_ER_IRQHandler",
"I2C2_EV_IRQHandler",
"I2C2_ER_IRQHandler",
"SPI1_IRQHandler",
"SPI2_IRQHandler",
"USART1_IRQHandler",
"USART2_IRQHandler",
"USART3_IRQHandler",
"EXTI15_10_IRQHandler",
"RTC_Alarm_IRQHandler",
"OTG_FS_WKUP_IRQHandler",
"TIM8_BRK_TIM12_IRQHandler",
"TIM8_UP_TIM13_IRQHandler",
"TIM8_TRG_COM_TIM14_IRQHandler",
"TIM8_CC_IRQHandler",
"DMA1_Stream7_IRQHandler",
"FSMC_IRQHandler",
"SDIO_IRQHandler",
"TIM5_IRQHandler",
"SPI3_IRQHandler",
"UART4_IRQHandler",
"UART5_IRQHandler",
"TIM6_DAC_IRQHandler",
"TIM7_IRQHandler",
"DMA2_Stream0_IRQHandler",
"DMA2_Stream1_IRQHandler",
"DMA2_Stream2_IRQHandler",
"DMA2_Stream3_IRQHandler",
"DMA2_Stream4_IRQHandler",
"ETH_IRQHandler",
"ETH_WKUP_IRQHandler",
"CAN2_TX_IRQHandler",
"CAN2_RX0_IRQHandler",
"CAN2_RX1_IRQHandler",
"CAN2_SCE_IRQHandler",
"OTG_FS_IRQHandler",
"DMA2_Stream5_IRQHandler",
"DMA2_Stream6_IRQHandler",
"DMA2_Stream7_IRQHandler",
"USART6_IRQHandler",
"I2C3_EV_IRQHandler",
"I2C3_ER_IRQHandler",
"OTG_HS_EP1_OUT_IRQHandler",
"OTG_HS_EP1_IN_IRQHandler",
"OTG_HS_WKUP_IRQHandler",
"OTG_HS_IRQHandler",
"DCMI_IRQHandler",
"HASH_RNG_IRQHandler",
"FPU_IRQHandler"
]

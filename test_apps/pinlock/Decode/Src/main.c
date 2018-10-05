/**
  ******************************************************************************
  * @file    FatFs/FatFs_USBDisk/Src/main.c
  * @author  MCD Application Team
  * @version V1.3.4
  * @date    06-May-2016
**/

/* Includes ------------------------------------------------------------------*/
#include "main.h"
#define STOP_TIMING asm volatile("mov r0, 0xFF \n\t" \
                                 "svc 0xFF \n\t":::"r0","memory")

/* Private typedef -----------------------------------------------------------*/
/* Private define ------------------------------------------------------------*/
/* Private macro -------------------------------------------------------------*/
/* Private variables ---------------------------------------------------------*/


uint8_t aTxBuffer[] = "Please enter your password:\n";

unsigned char PinRxBuffer[PINRXBUFFSIZE];
unsigned char LockRxBuffer[LOCKRXBUFFSIZE];
unsigned char key[32];
unsigned char key_in[32];
unsigned char pin[] = "1995\n";

UART_HandleTypeDef UartHandle;
/* UART handler declaration */
UART_HandleTypeDef UartHandle;
__IO ITStatus UartReady = RESET;

/* Private function prototypes -----------------------------------------------*/
static void SystemClock_Config(void);
static void Error_Handler(void);
static void Program_Init(void);
static void print(unsigned char*,int len);
/* Private functions ---------------------------------------------------------*/

/**
  * @brief  Main program
  * @param  None
  * @retval None
  */

unsigned char str[STRSIZE];   //will be used for sprintf

void lock(){
  BSP_LED_Off(LED4);
}

void unlock(){
  BSP_LED_On(LED4);
}

void rx_from_uart(uint32_t size){
    if (size > PINRXBUFFSIZE){
        Error_Handler();
    }
    if(HAL_UART_Receive_IT(&UartHandle, (uint8_t *)PinRxBuffer, size) != HAL_OK) {
        Error_Handler();
    }
    /*##- Wait for the end of the transfer ###################################*/
    while (UartReady != SET) {}
    /* Reset transmission flag */
    UartReady = RESET;
}

int main(void)
{
  int len;
  int unlock_count = 0;

  unsigned int one = 1;
  unsigned int exp;
  unsigned int ms;
  static char locked[]="System Locked\n";
  static char enter[] = "Enter Pin:\n";
  static char unlocked[] = "Unlocked\n";
  static char incorrect[] = "Incorrect Pin\n";
  static char waiting[] = "waiting...\n";
  static char lockout[] = "System Lockout\n";

  Program_Init();
  mbedtls_sha256((unsigned char*)pin,PINBUFFSIZE,key,0);
  while (1) {

    //BSP_LED_Off(LED4);
    //printf("System Locked\n");
    lock();
    print(locked,sizeof(locked));
    //BSP_LED_On(LED6);
    unsigned int failures = 0;
    // In Locked State
    while(1) {
        print(enter,sizeof(enter));
        rx_from_uart(5);
        //hash password received from uart
        mbedtls_sha256((unsigned char*)PinRxBuffer,PINRXBUFFSIZE,key_in,0);
        int i;
        for(i = 0; i < 32; i++) {
            if(key[i]!=key_in[i]) break;
        }
        if (i == 32) {
            print(unlocked,sizeof(unlocked));
            unlock_count++;
            if (unlock_count >= 100){
                STOP_TIMING;
            }
            break;
        }

  	  failures++; //increment number of failures
  	  //printf("Incorrect Pin\n");
      print(incorrect,sizeof(incorrect));
  	  if (failures > 5 && failures <= 10) {

        exp = one << failures;  // essentially 2^failures
        ms = 78*exp;   // after 5 tries, start waiting around 5 secs and then doubles
        print(waiting,sizeof(waiting));
        HAL_Delay(ms);

  	  }
	  else if(failures > 10) {
	    //printf("System Lockout\n");
        print(lockout,sizeof(lockout));
	    //BSP_LED_On(LED3);
	    while(1){}
	  }

    }

    unlock();
    // wait for lock command
    while (1) {
        rx_from_uart(2);
        if (PinRxBuffer[0] == '0'){
            break;
        }
    }
    lock();
  }

  //backup while loop
  while(1) {

  }
}


// Call all initializations for program

static void Program_Init (void) {

  /* STM32F4xx HAL library initialization:
       - Configure the Flash prefetch, instruction and Data caches
       - Configure the Systick to generate an interrupt each 1 msec
       - Set NVIC Group Priority to 4
       - Global MSP (MCU Support Package) initialization
     */
  HAL_Init();

  /* Configure LEDs */
  BSP_LED_Init(LED4);
  BSP_LED_Init(LED5);
  BSP_LED_Init(LED3);
  BSP_LED_Init(LED6);

  /* Configure the system clock to 168 MHz */
  SystemClock_Config();

   /*##-1- Configure the UART peripheral ######################################*/
  /* Put the USART peripheral in the Asynchronous mode (UART Mode) */
  /* UART1 configured as follow:
      - Word Length = 8 Bits
      - Stop Bit = One Stop bit
      - Parity = None
      - BaudRate = 9600 baud
      - Hardware flow control disabled (RTS and CTS signals) */
  UartHandle.Instance          = USARTx;

  UartHandle.Init.BaudRate     = 115200;
  UartHandle.Init.WordLength   = UART_WORDLENGTH_8B;
  UartHandle.Init.StopBits     = UART_STOPBITS_1;
  UartHandle.Init.Parity       = UART_PARITY_NONE;
  UartHandle.Init.HwFlowCtl    = UART_HWCONTROL_NONE;
  UartHandle.Init.Mode         = UART_MODE_TX_RX;
  UartHandle.Init.OverSampling = UART_OVERSAMPLING_16;

  if(HAL_UART_Init(&UartHandle) != HAL_OK)
  {
    Error_Handler();
  }

  //setbuf(stdout,NULL);
}


/**
  * @brief  System Clock Configuration
  *         The system Clock is configured as follow :
  *            System Clock source            = PLL (HSE)
  *            SYSCLK(Hz)                     = 168000000
  *            HCLK(Hz)                       = 168000000
  *            AHB Prescaler                  = 1
  *            APB1 Prescaler                 = 4
  *            APB2 Prescaler                 = 2
  *            HSE Frequency(Hz)              = 8000000
  *            PLL_M                          = 8
  *            PLL_N                          = 336
  *            PLL_P                          = 2
  *            PLL_Q                          = 7
  *            VDD(V)                         = 3.3
  *            Main regulator output voltage  = Scale1 mode
  *            Flash Latency(WS)              = 5
  * @param  None
  * @retval None
  */
static void SystemClock_Config  (void)
{
  RCC_ClkInitTypeDef RCC_ClkInitStruct;
  RCC_OscInitTypeDef RCC_OscInitStruct;

  /* Enable Power Control clock */
  __HAL_RCC_PWR_CLK_ENABLE();

  /* The voltage scaling allows optimizing the power consumption when the device is
     clocked below the maximum system frequency, to update the voltage scaling value
     regarding system frequency refer to product datasheet.  */
  __HAL_PWR_VOLTAGESCALING_CONFIG(PWR_REGULATOR_VOLTAGE_SCALE1);

  /* Enable HSE Oscillator and activate PLL with HSE as source */
  RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSE;
  RCC_OscInitStruct.HSEState = RCC_HSE_ON;
  RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
  RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSE;
  RCC_OscInitStruct.PLL.PLLM = 8;
  RCC_OscInitStruct.PLL.PLLN = 336;
  RCC_OscInitStruct.PLL.PLLP = RCC_PLLP_DIV2;
  RCC_OscInitStruct.PLL.PLLQ = 7;
  if(HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
  {
    Error_Handler();
  }

  /* Select PLL as system clock source and configure the HCLK, PCLK1 and PCLK2
     clocks dividers */
  RCC_ClkInitStruct.ClockType = (RCC_CLOCKTYPE_SYSCLK | RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2);
  RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
  RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
  RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV4;
  RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV2;
  if(HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_5) != HAL_OK)
  {
    Error_Handler();
  }

  /* STM32F405x/407x/415x/417x Revision Z devices: prefetch is supported  */
  if (HAL_GetREVID() == 0x1001)
  {
    /* Enable the Flash prefetch */
    __HAL_FLASH_PREFETCH_BUFFER_ENABLE();
  }
}

/**
  * @brief  Tx Transfer completed callback
  * @param  UartHandle: UART handle.
  * @note   This example shows a simple way to report end of IT Tx transfer, and
  *         you can add your own implementation.
  * @retval None
  */
void HAL_UART_TxCpltCallback(UART_HandleTypeDef *UartHandle)
{
  /* Set transmission flag: transfer complete */
  UartReady = SET;

  /* Turn LED6 on: Transfer in transmission process is correct */
  //BSP_LED_On(LED6);
}

/**
  * @brief  Rx Transfer completed callback
  * @param  UartHandle: UART handle
  * @note   This example shows a simple way to report end of IT Rx transfer, and
  *         you can add your own implementation.
  * @retval None
  */
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *UartHandle)
{
  /* Set transmission flag: transfer complete */
  UartReady = SET;

  /* Turn LED4 on: Transfer in reception process is correct */
  //BSP_LED_On(LED4);
}

/**
  * @brief  UART error callbacks
  * @param  UartHandle: UART handle
  * @note   This example shows a simple way to report transfer error, and you can
  *         add your own implementation.
  * @retval None
  */
 void HAL_UART_ErrorCallback(UART_HandleTypeDef *UartHandle)
{
  /* Turn LED3 on: Transfer error in reception/transmission process */
  //BSP_LED_On(LED3);
}


// FOR printf REDIRECT:


//void _sbrk() {

//}

/*
int _write(int fd, char *buf, size_t count) {

  if (HAL_UART_Transmit_IT(&UartHandle, (uint8_t *) buf, count) != HAL_OK) {
    Error_Handler();
  }


  //##- Wait for the end of the transfer ###################################
  while (UartReady != SET)
  {
  }

  // Reset transmission flag
  UartReady = RESET;

  return count;
}

*/

static void print(unsigned char* str, int len) {

  UartReady = RESET;

  if (HAL_UART_Transmit_IT(&UartHandle, (uint8_t *) str, len) != HAL_OK) {
    Error_Handler();
  }
  //##- Wait for the end of the transfer ###################################
  while (UartReady != SET)
  {
  }
  // Reset transmission flag
  UartReady = RESET;

}



/**
  * @brief  This function is executed in case of error occurrence.
  * @param  None
  * @retval None
  */
static void Error_Handler(void)
{
  /* Turn LED5 on */
  BSP_LED_On(LED5);
  while(1)
  {
  }
}

#ifdef  USE_FULL_ASSERT
/**
  * @brief  Reports the name of the source file and the source line number
  *         where the assert_param error has occurred.
  * @param  file: pointer to the source file name
  * @param  line: assert_param error line source number
  * @retval None
  */
void assert_failed(uint8_t* file, uint32_t line)
{
  /* User can add his own implementation to report the file name and line number,
     ex: printf("Wrong parameters value: file %s on line %d\r\n", file, line) */

  /* Infinite loop */
  while (1)
  {
  }
}
#endif




/******************END OF FILE****/
